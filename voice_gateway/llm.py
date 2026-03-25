"""LLM predict functions for Databricks Model Serving endpoints."""
from __future__ import annotations

from typing import Any

import httpx


def make_predict_fn(host: str, token: str, endpoint: str):
    """Create an async predict function for a Databricks Model Serving endpoint."""
    url = f"{host.rstrip('/')}/serving-endpoints/{endpoint}/invocations"
    headers = {"Authorization": f"Bearer {token}"}

    async def predict(messages: list[dict], temperature: float = 0.0, max_tokens: int = 200, **kwargs) -> str:
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Standard chat completion response
            if "choices" in data and data["choices"]:
                return data["choices"][0].get("message", {}).get("content", "")
            # Direct content
            if "content" in data:
                return data["content"]
            return str(data)

    return predict
