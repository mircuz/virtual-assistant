"""Text-to-Speech client for Kokoro TTS Databricks App."""
from __future__ import annotations

import httpx


class TTSClient:
    """Calls the Kokoro TTS Databricks App."""

    def __init__(self, url: str, token: str, voice: str = "if_sara"):
        if not url.startswith("http"):
            url = f"https://{url}"
        self._url = url.rstrip("/") + "/synthesize"
        self._headers = {"Authorization": f"Bearer {token}"}
        self._voice = voice

    async def synthesize(self, text: str) -> str:
        """Convert text to speech. Returns base64-encoded audio."""
        payload = {
            "text": text,
            "voice": self._voice,
            "language": "it",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self._url,
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("audio_base64", "")
