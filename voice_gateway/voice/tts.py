"""Text-to-Speech client for Databricks-hosted Kokoro endpoint."""
from __future__ import annotations

import httpx


class TTSClient:
    """Calls a Databricks Model Serving endpoint for Kokoro TTS."""

    def __init__(self, host: str, token: str, endpoint: str, voice: str = "af_sky"):
        if not host.startswith("http"):
            host = f"https://{host}"
        self._url = f"{host.rstrip('/')}/serving-endpoints/{endpoint}/invocations"
        self._headers = {"Authorization": f"Bearer {token}"}
        self._voice = voice

    async def synthesize(self, text: str) -> str:
        """Convert text to speech. Returns base64-encoded audio."""
        payload = {
            "dataframe_records": [
                {"text": text, "voice": self._voice, "language": "it"}
            ]
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self._url,
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            # MLflow pyfunc returns {"predictions": [{"audio_base64": "..."}]}
            if isinstance(data, dict):
                preds = data.get("predictions", [])
                if preds and isinstance(preds[0], dict):
                    return preds[0].get("audio_base64", "")
                if preds and isinstance(preds[0], str):
                    return preds[0]
                # Fallback for other response shapes
                for key in ("audio", "audio_base64", "result"):
                    if key in data:
                        val = data[key]
                        if isinstance(val, str):
                            return val
            return ""
