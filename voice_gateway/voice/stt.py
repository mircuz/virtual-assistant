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
        payload = {"dataframe_records": [{"audio": audio_base64}]}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                self._url,
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            # Whisper returns {"predictions": ["transcribed text"]}
            if isinstance(data, dict):
                preds = data.get("predictions", [])
                if preds and isinstance(preds[0], str):
                    return preds[0]
                return data.get("text", data.get("transcription", ""))
            return str(data)
