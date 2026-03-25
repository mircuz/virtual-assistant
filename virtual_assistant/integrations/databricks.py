"""
Databricks integration utilities.

Provides the predict_fn factory for calling Databricks Model Serving endpoints.

Supports two endpoint flavours:
  - Foundation Model APIs  (chat completions format, pay-per-token, always available)
  - Custom / external model endpoints  (legacy prompt format, requires a deployed endpoint)

Foundation Model endpoint names (recommended, no deployment needed):
  databricks-meta-llama-3-3-70b-instruct   ← good default
  databricks-meta-llama-3-1-70b-instruct
  databricks-dbrx-instruct
  databricks-mixtral-8x7b-instruct
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

# Endpoint names that use Databricks Foundation Model APIs (chat completions format).
# Any name starting with "databricks-" is treated as a Foundation Model endpoint.
_FOUNDATION_MODEL_PREFIX = "databricks-"


def load_env_file(env_path: str) -> None:
    """Load environment variables from a .env-style file."""
    path = Path(env_path)
    if not path.exists():
        raise FileNotFoundError(f"Env file not found: {env_path}")

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def _resolve_token(token: str | None) -> str:
    """Resolve Databricks token: explicit > env var > notebook context."""
    if token:
        return token
    token = os.getenv("DATABRICKS_TOKEN", "")
    if token:
        return token
    try:
        from dbruntime.databricks_repl_context import get_context  # type: ignore
        return get_context().apiToken
    except Exception:
        pass
    raise ValueError(
        "DATABRICKS_TOKEN is not configured and no Databricks notebook token is available. "
        "Set DATABRICKS_TOKEN in your env file or run inside a Databricks notebook."
    )


def create_databricks_predict_fn(
    host: str | None = None,
    token: str | None = None,
    endpoint: str | None = None,
    temperature: float = 0.3,
) -> Callable[[str, int], str]:
    """
    Create a prediction function backed by Databricks Model Serving.

    Signature of the returned callable: (prompt: str, max_tokens: int) -> str

    For Foundation Model endpoints (names starting with 'databricks-'), uses the
    OpenAI-compatible chat completions format — no custom endpoint deployment required.

    For custom endpoints, uses the legacy prompt/predictions format.

    Args:
        host:        Workspace URL. Defaults to DATABRICKS_HOST env var.
        token:       API token. Defaults to DATABRICKS_TOKEN env var or notebook context.
        endpoint:    Endpoint name. Defaults to DATABRICKS_ENDPOINT env var.
                     For real-time voice: "databricks-meta-llama-3-1-8b-instruct" (fastest).
                     For higher quality: "databricks-meta-llama-3-3-70b-instruct".
        temperature: Sampling temperature (default 0.3). Use 0.0 for structured/JSON output,
                     0.3 for natural conversational responses.
    """
    import requests

    host = (host or os.getenv("DATABRICKS_HOST", "")).rstrip("/")
    if not host:
        raise ValueError(
            "DATABRICKS_HOST is not configured. Set it in your env file or pass it explicitly."
        )

    token = _resolve_token(token)
    endpoint = (
        endpoint
        or os.getenv("DATABRICKS_ENDPOINT", "databricks-meta-llama-3-1-8b-instruct")
    )

    endpoint_url = f"{host}/serving-endpoints/{endpoint}/invocations"
    is_foundation_model = endpoint.startswith(_FOUNDATION_MODEL_PREFIX)

    def predict(prompt: str, max_tokens: int = 512) -> str:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        if is_foundation_model:
            payload: dict = {
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        else:
            payload = {"prompt": prompt, "max_tokens": max_tokens}

        response = requests.post(endpoint_url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        if "choices" in data and data["choices"]:
            choice = data["choices"][0]
            if "message" in choice:
                return choice["message"]["content"]
            if "text" in choice:
                return choice["text"]

        if "predictions" in data and data["predictions"]:
            pred = data["predictions"][0]
            if isinstance(pred, dict):
                return pred.get("response", pred.get("output", str(pred)))
            return str(pred)

        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                return first.get("response", first.get("output", str(first)))
            return str(first)

        raise RuntimeError(
            f"Unexpected response shape from endpoint '{endpoint}': {str(data)[:200]}"
        )

    return predict
