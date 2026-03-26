"""Speech-to-Text client for Databricks-hosted Whisper endpoint."""
from __future__ import annotations

import base64
import httpx


class STTClient:
    """Calls a Databricks Model Serving endpoint for Whisper STT."""

    def __init__(self, host: str, token: str, endpoint: str):
        if not host.startswith("http"):
            host = f"https://{host}"
        self._url = f"{host.rstrip('/')}/serving-endpoints/{endpoint}/invocations"
        self._headers = {"Authorization": f"Bearer {token}"}

    async def transcribe(self, audio_base64: str) -> str:
        """Send base64-encoded audio to Whisper endpoint, return text."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self._url,
                headers=self._headers,
                json={"audio": audio_base64, "language": "it"},
            )
            resp.raise_for_status()
            data = resp.json()
            # Handle various response shapes from model serving
            if isinstance(data, dict):
                return data.get("text", data.get("transcription", ""))
            return str(data)
