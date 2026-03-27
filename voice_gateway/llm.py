"""LLM predict functions for Databricks Model Serving endpoints."""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx


def make_predict_fn(host: str, token: str, endpoint: str):
    """Create an async predict function for a Databricks Model Serving endpoint."""
    if not host.startswith("http"):
        host = f"https://{host}"
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
            if "choices" in data and data["choices"]:
                return data["choices"][0].get("message", {}).get("content", "")
            if "content" in data:
                return data["content"]
            return str(data)

    async def predict_stream(messages: list[dict], temperature: float = 0.3, max_tokens: int = 200) -> AsyncIterator[str]:
        """Stream tokens from the LLM. Yields text chunks as they arrive."""
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        text = delta.get("content", "")
                        if text:
                            yield text
                    except json.JSONDecodeError:
                        continue

    predict.stream = predict_stream
    return predict
