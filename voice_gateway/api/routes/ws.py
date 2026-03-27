"""SSE streaming endpoint for real-time voice conversations.

Uses Server-Sent Events (SSE) for streaming LLM tokens + TTS audio chunks
back to the client, since Databricks Apps proxy doesn't support WebSocket.

Flow: POST /turn → SSE stream of tokens + audio chunks
"""
from __future__ import annotations

import asyncio
import json
import re
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from voice_gateway.api.models import TurnRequest

router = APIRouter(tags=["streaming"])


@router.post("/conversations/{session_id}/stream")
async def stream_turn(session_id: UUID, body: TurnRequest, request: Request):
    """Process a turn with streaming response: SSE of text tokens + TTS audio chunks."""
    app = request.app
    mgr = app.state.session_manager
    session = mgr.get_session(session_id)

    if not session:
        return StreamingResponse(
            _error_stream("Session not found"),
            media_type="text/event-stream",
        )

    # Get user text
    user_text = body.text
    if not user_text and body.audio_base64 and app.state.stt:
        user_text = await app.state.stt.transcribe(body.audio_base64)

    if not user_text:
        return StreamingResponse(
            _error_stream("No input"),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        _stream_turn(app, session, user_text),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_turn(app, session, user_text: str):
    """Generator that yields SSE events: transcript, token, audio, turn_end."""
    session.add_user_turn(user_text)

    # Emit the transcribed text
    yield _sse("transcript", {"text": user_text})
    yield _sse("status", {"status": "thinking"})

    # Build messages
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    services = getattr(session, "_services", [])
    staff = getattr(session, "_staff", [])

    enhanced_system = (
        f"{session.system_prompt}\n\n"
        f"Data e ora corrente: {now}\n"
        f"Servizi disponibili: {', '.join(services) if services else 'nessuno'}\n"
        f"Staff disponibile: {', '.join(staff) if staff else 'nessuno'}\n\n"
        "REGOLE TASSATIVE:\n"
        "- Rispondi SEMPRE in italiano, breve e naturale, 1-2 frasi massimo\n"
        "- NON usare MAI emoji, simboli o caratteri speciali\n"
        "- Parla come in una vera telefonata: colloquiale, diretto, umano\n"
        "- Usa frasi brevi e scorrevoli, facili da pronunciare ad alta voce"
    )

    messages = [{"role": "system", "content": enhanced_system}]
    messages.extend(session.history)

    # Stream LLM tokens, fire TTS asynchronously per clause
    predict_fn = app.state.llm_predict
    tts = app.state.tts
    full_text = ""
    sentence_buffer = ""
    # Queue of TTS futures — fire and collect in order
    tts_tasks: list[asyncio.Task] = []

    yield _sse("status", {"status": "speaking"})

    async for token in predict_fn.stream(messages, temperature=0.3, max_tokens=200):
        full_text += token
        sentence_buffer += token
        yield _sse("token", {"text": token})

        # On sentence boundary, fire TTS in background
        if tts and re.search(r'[.!?,;]\s*$', sentence_buffer):
            chunk = sentence_buffer.strip()
            sentence_buffer = ""
            if chunk:
                task = asyncio.create_task(tts.synthesize(chunk))
                tts_tasks.append(task)
                # If first chunk is ready, yield it immediately
                if tts_tasks[0].done():
                    try:
                        audio = tts_tasks.pop(0).result()
                        if audio:
                            yield _sse("audio", {"audio_base64": audio})
                    except Exception:
                        tts_tasks.pop(0) if tts_tasks else None

    # TTS remaining buffer
    if tts and sentence_buffer.strip():
        task = asyncio.create_task(tts.synthesize(sentence_buffer.strip()))
        tts_tasks.append(task)

    # Drain all pending TTS tasks in order
    for task in tts_tasks:
        try:
            audio = await task
            if audio:
                yield _sse("audio", {"audio_base64": audio})
        except Exception:
            pass

    session.add_assistant_turn(full_text)
    yield _sse("turn_end", {"full_text": full_text})


async def _error_stream(message: str):
    yield _sse("error", {"message": message})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
