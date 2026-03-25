"""
Text-to-Speech Manager (MVP)

Minimal TTS wrapper for a Databricks Model Serving endpoint (Kokoro or compatible).
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass
class TTSResult:
    """Result of TTS generation."""

    audio_path: str
    text_path: str | None
    duration_seconds: float | None
    success: bool
    error: str | None = None


class TTSManager:
    """Simple endpoint-backed TTS manager."""

    def __init__(self, output_dir: str | None = None):
        volume_base = os.getenv("VOLUME_BASE", "/tmp/voice_assistant")
        self.output_dir = output_dir or str(Path(volume_base) / "responses")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        self.host = os.getenv("DATABRICKS_HOST", "").rstrip("/")
        self.endpoint = os.getenv("DATABRICKS_TTS_ENDPOINT", "kokoro-tts-endpoint")
        self.voice = os.getenv("TTS_VOICE", "af_sky")

    def _token(self) -> str:
        token = os.getenv("DATABRICKS_TOKEN", "")
        if token:
            return token
        raise RuntimeError("Missing DATABRICKS_TOKEN for endpoint TTS.")

    def _url(self) -> str:
        if not self.host:
            raise RuntimeError("Missing DATABRICKS_HOST for endpoint TTS.")
        return f"{self.host}/serving-endpoints/{self.endpoint}/invocations"

    def _extract_audio_base64(self, payload: object) -> str | None:
        if isinstance(payload, dict):
            for key in ("audio", "audio_base64", "wav_base64", "output_audio"):
                value = payload.get(key)
                if isinstance(value, str) and value:
                    return value
            for nested in ("predictions", "prediction", "result", "outputs"):
                found = self._extract_audio_base64(payload.get(nested))
                if found:
                    return found
        if isinstance(payload, list):
            for item in payload:
                found = self._extract_audio_base64(item)
                if found:
                    return found
        return None

    def speak(
        self,
        text: str,
        input_wav: str | None = None,
        output_filename: str = "response.wav",
    ) -> TTSResult:
        del input_wav  # not used in MVP endpoint flow

        audio_path = Path(self.output_dir) / output_filename
        meta_path = Path(self.output_dir) / output_filename.replace(".wav", ".json")
        headers = {"Authorization": f"Bearer {self._token()}"}
        payload = {"text": text, "voice": self.voice}

        try:
            response = requests.post(self._url(), json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            audio_b64 = self._extract_audio_base64(data)
            if not audio_b64:
                return TTSResult(
                    audio_path=str(audio_path),
                    text_path=str(meta_path),
                    duration_seconds=None,
                    success=False,
                    error=f"No audio found in TTS response: {data}",
                )

            audio_path.write_bytes(base64.b64decode(audio_b64))
            meta_path.write_text(json.dumps(data, indent=2))
            return TTSResult(
                audio_path=str(audio_path),
                text_path=str(meta_path),
                duration_seconds=self._get_audio_duration(str(audio_path)),
                success=True,
            )
        except Exception as exc:
            return TTSResult(
                audio_path=str(audio_path),
                text_path=str(meta_path),
                duration_seconds=None,
                success=False,
                error=str(exc),
            )

    def speak_filler(self, filler_text: str) -> TTSResult:
        return self.speak(filler_text, output_filename=f"filler_{hash(filler_text) % 10000}.wav")

    def _get_audio_duration(self, audio_path: str) -> float | None:
        try:
            import wave

            with wave.open(audio_path, "rb") as wav:
                return wav.getnframes() / wav.getframerate()
        except Exception:
            return None


class MockTTSManager(TTSManager):
    """Mock TTS manager for testing."""

    def speak(
        self,
        text: str,
        input_wav: str | None = None,
        output_filename: str = "response.wav",
    ) -> TTSResult:
        del input_wav
        output_wav = str(Path(self.output_dir) / output_filename)
        Path(output_wav).touch()
        return TTSResult(
            audio_path=output_wav,
            text_path=None,
            duration_seconds=len(text) * 0.05,
            success=True,
        )


def get_tts_manager(mock: bool = False) -> TTSManager:
    if mock or os.getenv("MOCK_TTS", "false").lower() == "true":
        return MockTTSManager()
    return TTSManager()
