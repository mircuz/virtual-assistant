"""SSE streaming endpoint — single GPT-Audio call for audio-in → LLM → audio-out.

Eliminates separate STT and TTS calls. GPT-Audio handles everything in one shot.
For text input, falls back to Haiku agent + GPT-Audio TTS.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import struct
from uuid import UUID

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from voice_gateway.api.models import TurnRequest
from voice_gateway.conversation.agent import ConversationAgent

router = APIRouter(tags=["streaming"])


def _pcm16_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits: int = 16) -> bytes:
    data_size = len(pcm_data)
    buf = io.BytesIO()
    buf.write(b'RIFF')
    buf.write(struct.pack('<I', 36 + data_size))
    buf.write(b'WAVE')
    buf.write(b'fmt ')
    buf.write(struct.pack('<I', 16))
    buf.write(struct.pack('<HHIIHH', 1, channels, sample_rate, sample_rate * channels * bits // 8, channels * bits // 8, bits))
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

    # Determine input mode
    has_audio = bool(body.audio_base64)
    has_text = bool(body.text)

    if not has_audio and not has_text:
        return StreamingResponse(_error_stream("No input"), media_type="text/event-stream")

    if has_audio:
        # Audio path: single GPT-Audio call (audio-in → LLM → audio-out)
        return StreamingResponse(
            _stream_audio_turn(app, session, body.audio_base64),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        # Text path: Haiku agent → execute action → GPT-Audio TTS
        return StreamingResponse(
            _stream_text_turn(app, session, body.text),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )


async def _stream_audio_turn(app, session, audio_b64: str):
    """Single GPT-Audio call: audio input → LLM reasoning → audio output."""
    yield _sse("status", {"status": "thinking"})

    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    services = getattr(session, "_services", [])
    staff = getattr(session, "_staff", [])

    voice_system = (
        f"{session.system_prompt}\n\n"
        f"Data e ora: {now}\n"
        f"Servizi: {', '.join(services) if services else 'nessuno'}\n"
        f"Staff: {', '.join(staff) if staff else 'nessuno'}\n\n"
        "REGOLE:\n"
        "- Rispondi in italiano, breve e naturale, 1-2 frasi max\n"
        "- NON usare emoji o simboli\n"
        "- Tono allegro e solare, come al telefono\n"
        "- Se il cliente saluta o ringrazia per concludere, rispondi con un breve saluto finale\n"
        "- Se il cliente dice il suo nome, salutalo per nome"
    )

    # Build messages with audio input
    messages = [{"role": "system", "content": voice_system}]
    # Add conversation history (text only)
    messages.extend(session.history)
    # Add the new audio input
    messages.append({
        "role": "user",
        "content": [{"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}}]
    })

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
        "audio": {"voice": "nova", "format": "pcm16"},
        "stream": True,
    }

    full_transcript = ""
    user_transcript = ""
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

                    audio_delta = delta.get("audio", {})
                    transcript = audio_delta.get("transcript", "")
                    if transcript:
                        full_transcript += transcript
                        yield _sse("token", {"text": transcript})

                    audio_data = audio_delta.get("data", "")
                    if audio_data:
                        pcm_bytes = base64.b64decode(audio_data)
                        pcm_buffer += pcm_bytes
                        while len(pcm_buffer) >= 24000:
                            chunk_pcm = pcm_buffer[:24000]
                            pcm_buffer = pcm_buffer[24000:]
                            wav = _pcm16_to_wav(chunk_pcm)
                            yield _sse("audio", {"audio_base64": base64.b64encode(wav).decode()})
                except json.JSONDecodeError:
                    continue

    if pcm_buffer:
        wav = _pcm16_to_wav(pcm_buffer)
        yield _sse("audio", {"audio_base64": base64.b64encode(wav).decode()})

    # GPT-Audio transcribes the user input implicitly — we infer from context
    # Add both turns to history
    session.add_user_turn("[audio input]")
    session.add_assistant_turn(full_transcript)

    # Detect goodbye from the response
    goodbye_words = ["arrivederci", "a presto", "buona giornata", "alla prossima", "ciao ciao"]
    is_goodbye = any(w in full_transcript.lower() for w in goodbye_words)

    yield _sse("turn_end", {"full_text": full_transcript, "end_call": is_goodbye})


async def _stream_text_turn(app, session, user_text: str):
    """Text input: Haiku agent → execute action → GPT-Audio TTS."""
    session.add_user_turn(user_text)
    yield _sse("transcript", {"text": user_text})
    yield _sse("status", {"status": "thinking"})

    # Agent extracts intent
    agent = ConversationAgent(predict_fn=app.state.llm_predict)
    response_text, action, args = await agent.process(
        system_prompt=session.system_prompt,
        history=session.history,
        services=getattr(session, "_services", []),
        staff=getattr(session, "_staff", []),
    )

    # Execute booking action
    action_context = ""
    if action == "provide_name":
        from voice_gateway.api.routes.conversations import _identify_customer
        result = await _identify_customer(app, session, args.get("name", ""))
        action_context = f"[Cliente identificato: {json.dumps(result, default=str, ensure_ascii=False)}]"
    elif action in ("check_availability", "list_appointments", "ask_service_info", "book", "cancel", "reschedule"):
        from voice_gateway.api.routes.conversations import _execute_action
        result = await _execute_action(app, session, action, args)
        if result:
            action_context = f"[Risultato {action}: {json.dumps(result, default=str, ensure_ascii=False)}]"

    # GPT-Audio for voice response
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    services = getattr(session, "_services", [])
    staff = getattr(session, "_staff", [])

    voice_system = (
        f"{session.system_prompt}\n\n"
        f"Data e ora: {now} | Servizi: {', '.join(services)} | Staff: {', '.join(staff)}\n"
        "Rispondi in italiano, breve, allegro, come al telefono. No emoji."
    )

    messages = [{"role": "system", "content": voice_system}]
    messages.extend(session.history)
    if action_context:
        messages.append({"role": "system", "content": action_context + "\nRispondi al cliente basandoti su questo risultato."})

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
        "audio": {"voice": "nova", "format": "pcm16"},
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
                    audio_delta = delta.get("audio", {})
                    transcript = audio_delta.get("transcript", "")
                    if transcript:
                        full_transcript += transcript
                        yield _sse("token", {"text": transcript})
                    audio_data = audio_delta.get("data", "")
                    if audio_data:
                        pcm_bytes = base64.b64decode(audio_data)
                        pcm_buffer += pcm_bytes
                        while len(pcm_buffer) >= 24000:
                            chunk_pcm = pcm_buffer[:24000]
                            pcm_buffer = pcm_buffer[24000:]
                            wav = _pcm16_to_wav(chunk_pcm)
                            yield _sse("audio", {"audio_base64": base64.b64encode(wav).decode()})
                except json.JSONDecodeError:
                    continue

    if pcm_buffer:
        wav = _pcm16_to_wav(pcm_buffer)
        yield _sse("audio", {"audio_base64": base64.b64encode(wav).decode()})

    session.add_assistant_turn(full_transcript)
    yield _sse("turn_end", {"full_text": full_transcript, "end_call": action == "goodbye"})


async def _error_stream(message: str):
    yield _sse("error", {"message": message})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
