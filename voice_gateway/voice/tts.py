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
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self._url,
                headers=self._headers,
                json={"text": text, "voice": self._voice, "language": "it"},
            )
            resp.raise_for_status()
            data = resp.json()
            # Extract audio from various response shapes
            if isinstance(data, dict):
                for key in ("audio", "audio_base64", "predictions", "result"):
                    if key in data:
                        val = data[key]
                        if isinstance(val, str):
                            return val
                        if isinstance(val, list) and val:
                            return val[0] if isinstance(val[0], str) else str(val[0])
            return ""
