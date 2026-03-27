"""Kokoro TTS as a lightweight FastAPI service (Databricks App)."""
from __future__ import annotations

import base64
import io
import logging

from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger("tts_service")


class TTSRequest(BaseModel):
    text: str
    voice: str = "if_sara"
    language: str = "i"
    speed: float = 1.0


class TTSResponse(BaseModel):
    audio_base64: str
    sample_rate: int = 24000


_model = None

MODEL_DIR = "/tmp/kokoro_models"
ONNX_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"


def _download_if_missing(url: str, path: str):
    import os
    if os.path.exists(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    logger.info("Downloading %s ...", url)
    import urllib.request
    urllib.request.urlretrieve(url, path)
    logger.info("Saved to %s (%d bytes)", path, os.path.getsize(path))


def get_model():
    global _model
    if _model is None:
        import os
        import kokoro_onnx
        onnx_path = os.path.join(MODEL_DIR, "kokoro-v1.0.onnx")
        voices_path = os.path.join(MODEL_DIR, "voices-v1.0.bin")
        _download_if_missing(ONNX_URL, onnx_path)
        _download_if_missing(VOICES_URL, voices_path)
        _model = kokoro_onnx.Kokoro(onnx_path, voices_path)
        logger.info("Kokoro ONNX model loaded")
    return _model


def create_app() -> FastAPI:
    app = FastAPI(title="Kokoro TTS Service", version="1.0.0")

    @app.on_event("startup")
    async def startup():
        logger.info("Loading Kokoro TTS model...")
        get_model()
        logger.info("TTS model ready")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/synthesize", response_model=TTSResponse)
    async def synthesize(req: TTSRequest):
        import soundfile as sf
        import numpy as np

        model = get_model()
        audio, sr = model.create(
            req.text, voice=req.voice, lang=req.language, speed=req.speed
        )

        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV", subtype="PCM_16")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        return TTSResponse(audio_base64=b64, sample_rate=sr)

    # Also support the MLflow-style invocations endpoint for compatibility
    @app.post("/invocations")
    async def invocations(body: dict):
        import soundfile as sf

        records = body.get("dataframe_records", [body])
        model = get_model()
        predictions = []

        for rec in records:
            text = rec.get("text", "")
            voice = rec.get("voice", "if_sara")
            lang = rec.get("language", "i")

            audio, sr = model.create(text, voice=voice, lang=lang, speed=1.0)

            buf = io.BytesIO()
            sf.write(buf, audio, sr, format="WAV", subtype="PCM_16")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            predictions.append({"audio_base64": b64})

        return {"predictions": predictions}

    return app
