"""SSE streaming endpoint with GPT-Audio for combined LLM+TTS.

Flow: POST /stream → SSE stream of transcript tokens + PCM16 audio chunks
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import re
import struct
from uuid import UUID

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from voice_gateway.api.models import TurnRequest

router = APIRouter(tags=["streaming"])


def _pcm16_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits: int = 16) -> bytes:
    """Convert raw PCM16 bytes to WAV format."""
    data_size = len(pcm_data)
    buf = io.BytesIO()
    # RIFF header
    buf.write(b'RIFF')
    buf.write(struct.pack('<I', 36 + data_size))
    buf.write(b'WAVE')
    # fmt chunk
    buf.write(b'fmt ')
    buf.write(struct.pack('<I', 16))
    buf.write(struct.pack('<HHIIHH', 1, channels, sample_rate, sample_rate * channels * bits // 8, channels * bits // 8, bits))
    # data chunk
    buf.write(b'data')
    buf.write(struct.pack('<I', data_size))
    buf.write(pcm_data)
    return buf.getvalue()


@router.post("/conversations/{session_id}/stream")
async def stream_turn(session_id: UUID, body: TurnRequest, request: Request):
    app = request.app
    mgr = app.state.session_manager
    session = mgr.get_session(session_id)

    if not session:
        return StreamingResponse(_error_stream("Session not found"), media_type="text/event-stream")

    user_text = body.text
    if not user_text and body.audio_base64 and app.state.stt:
        user_text = await app.state.stt.transcribe(body.audio_base64)

    if not user_text:
        return StreamingResponse(_error_stream("No input"), media_type="text/event-stream")

    return StreamingResponse(
        _stream_turn(app, session, user_text),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_turn(app, session, user_text: str):
    session.add_user_turn(user_text)
    yield _sse("transcript", {"text": user_text})
    yield _sse("status", {"status": "thinking"})

    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    services = getattr(session, "_services", [])
    staff = getattr(session, "_staff", [])

    enhanced_system = (
        f"{session.system_prompt}\n\n"
        f"Data e ora corrente: {now}\n"
        f"Servizi disponibili: {', '.join(services) if services else 'nessuno'}\n"
        f"Staff disponibile: {', '.join(staff) if staff else 'nessuno'}\n\n"
        "REGOLE TASSATIVE PER LA RISPOSTA:\n"
        "- Rispondi SEMPRE in italiano, breve e naturale, 1-2 frasi massimo\n"
        "- NON usare MAI emoji, simboli, asterischi o caratteri speciali\n"
        "- Parla come in una vera telefonata: colloquiale, diretto, caldo\n"
        "- Usa un tono solare e accogliente, come chi ama il proprio lavoro\n"
        "- Usa espressioni naturali italiane: 'certo!', 'dimmi pure', 'figurati', 'ma dai!'\n"
        "- Frasi brevi e scorrevoli, facili da pronunciare ad alta voce\n"
        "- NON elencare prezzi a meno che non li chiedano"
    )

    messages = [{"role": "system", "content": enhanced_system}]
    messages.extend(session.history)

    # Use GPT-Audio for combined LLM+TTS (streaming)
    host = app.state._gpt_audio_host
    token = app.state._gpt_audio_token
    endpoint = app.state._gpt_audio_endpoint

    url = f"https://{host}/serving-endpoints/{endpoint}/invocations"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "messages": messages,
        "max_tokens": 150,
        "temperature": 0.4,
        "modalities": ["text", "audio"],
        "audio": {"voice": "coral", "format": "pcm16"},
        "stream": True,
    }

    full_transcript = ""
    pcm_buffer = b""

    yield _sse("status", {"status": "speaking"})

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
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})

                    # Text transcript tokens
                    audio_delta = delta.get("audio", {})
                    transcript = audio_delta.get("transcript", "")
                    if transcript:
                        full_transcript += transcript
                        yield _sse("token", {"text": transcript})

                    # PCM16 audio data chunks
                    audio_data = audio_delta.get("data", "")
                    if audio_data:
                        pcm_bytes = base64.b64decode(audio_data)
                        pcm_buffer += pcm_bytes
                        # Send audio in ~0.5s chunks (24000 Hz * 2 bytes * 0.5s = 24000 bytes)
                        while len(pcm_buffer) >= 24000:
                            chunk_pcm = pcm_buffer[:24000]
                            pcm_buffer = pcm_buffer[24000:]
                            wav = _pcm16_to_wav(chunk_pcm)
                            yield _sse("audio", {"audio_base64": base64.b64encode(wav).decode()})

                except json.JSONDecodeError:
                    continue

    # Flush remaining PCM buffer
    if pcm_buffer:
        wav = _pcm16_to_wav(pcm_buffer)
        yield _sse("audio", {"audio_base64": base64.b64encode(wav).decode()})

    session.add_assistant_turn(full_transcript)
    yield _sse("turn_end", {"full_text": full_transcript})


async def _error_stream(message: str):
    yield _sse("error", {"message": message})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
