"""Realtime API token endpoint — generates ephemeral tokens for WebRTC sessions."""
from __future__ import annotations

import json
import os
from datetime import datetime
from uuid import UUID

import httpx
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1/realtime", tags=["realtime"])

OPENAI_REALTIME_URL = "https://api.openai.com/v1/realtime/sessions"
OPENAI_MODEL = "gpt-4o-mini-realtime-preview-2024-12-17"


@router.post("/token")
async def get_realtime_token(request: Request, shop_id: str = Query(...)):
    """Generate an ephemeral OpenAI Realtime API token with session config."""
    app = request.app
    openai_key = app.state._openai_key
    if not openai_key:
        return JSONResponse(status_code=500, content={"error": "OpenAI key not configured"})

    # Load shop data for the system prompt
    booking = app.state.booking_client
    shop = await booking.get_shop(shop_id)
    if not shop:
        return JSONResponse(status_code=404, content={"error": "Shop not found"})

    services = await booking.get_services(shop_id)
    staff = await booking.get_staff(shop_id)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    services_str = ", ".join(s.get("service_name", "") for s in services)
    staff_str = ", ".join(s.get("full_name", "") for s in staff)

    instructions = (
        f"{shop.get('personality', '')}\n"
        f"{shop.get('tone_instructions', '')}\n\n"
        f"Data e ora corrente: {now}\n"
        f"Servizi disponibili: {services_str}\n"
        f"Staff disponibile: {staff_str}\n\n"
        "REGOLE:\n"
        "- Rispondi SEMPRE in italiano\n"
        "- Sii breve e naturale, come una vera telefonata\n"
        "- Tono allegro, solare e accogliente\n"
        "- NON usare emoji o simboli\n"
        "- Se il cliente dice il suo nome, salutalo e chiedi come puoi aiutare\n"
        "- Se chiede servizi, elencali brevemente\n"
        "- Se vuole prenotare o sapere la disponibilità, usa lo strumento check_availability\n"
        "- Se il cliente saluta per andarsene, salutalo calorosamente e chiudi"
    )

    # Define tools for function calling
    tools = [
        {
            "type": "function",
            "name": "check_availability",
            "description": "Controlla la disponibilità per un servizio in una data specifica",
            "parameters": {
                "type": "object",
                "properties": {
                    "services": {"type": "array", "items": {"type": "string"}, "description": "Nomi dei servizi richiesti"},
                    "date": {"type": "string", "description": "Data in formato YYYY-MM-DD"},
                    "staff_name": {"type": "string", "description": "Nome dello staff preferito (opzionale)"},
                },
                "required": ["services"],
            },
        },
        {
            "type": "function",
            "name": "get_services",
            "description": "Ottieni la lista completa dei servizi con prezzi e durata",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "type": "function",
            "name": "create_customer",
            "description": "Registra un nuovo cliente con nome e telefono",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nome completo del cliente"},
                    "phone": {"type": "string", "description": "Numero di telefono (opzionale)"},
                },
                "required": ["name"],
            },
        },
    ]

    # Request ephemeral token from OpenAI
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            OPENAI_REALTIME_URL,
            headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
            json={
                "model": OPENAI_MODEL,
                "voice": "coral",
                "instructions": instructions,
                "tools": tools,
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 800,
                    "create_response": True,
                },
                "input_audio_transcription": {"model": "gpt-4o-mini-transcribe"},
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "token": data["client_secret"]["value"],
        "expires_at": data["client_secret"]["expires_at"],
        "model": data.get("model"),
        "shop": {
            "id": shop_id,
            "name": shop.get("name"),
            "welcome_message": shop.get("welcome_message", "Ciao, benvenuto!"),
        },
        "services": [{"id": s.get("id"), "name": s.get("service_name")} for s in services],
        "staff": [{"id": s.get("id"), "name": s.get("full_name")} for s in staff],
    }
