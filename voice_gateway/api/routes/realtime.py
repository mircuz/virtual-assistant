"""Realtime API: token generation + function call proxy for booking actions."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from uuid import UUID

import httpx
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/realtime", tags=["realtime"])

OPENAI_REALTIME_URL = "https://api.openai.com/v1/realtime/sessions"
OPENAI_MODEL = "gpt-realtime"


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
        "# IDENTITÀ\n"
        f"{shop.get('personality', '')}\n\n"
        "# COME PARLI\n"
        f"{shop.get('tone_instructions', '')}\n\n"
        "Regole di stile (sempre valide):\n"
        "- Frasi brevi, come al telefono — mai da email\n"
        '- Usa riempitivi naturali: "allora…", "ok perfetto", "dimmi", "un attimo che controllo", "mmm", "aspetta"\n'
        '- Quando controlli qualcosa dillo ad alta voce: "un secondo ti cerco l\'agenda…"\n'
        '- Quando non capisci: "scusa mi è sfuggito, puoi ripetere?"\n'
        '- Quando confermi: "perfetto", "ci siamo", "benissimo"\n'
        "- Non ripetere tutti i dati del cliente — rispondi, non riassumere\n"
        "- Non sei un'intelligenza artificiale. Se te lo chiedono, sei la ragazza che risponde al telefono del salone.\n\n"
        "# ESEMPI DI COME SUONA AL TELEFONO\n"
        'Cliente: "Volevo prenotare un taglio"\n'
        'Tu: "Ok perfetto, quando ti andrebbe bene?"\n\n'
        'Cliente: "Giovedì pomeriggio?"\n'
        'Tu: "Allora… un attimo che controllo. Giovedì ho libero alle 15:30 o alle 17, cosa preferisci?"\n\n'
        'Cliente: "Aspetta, mi fai anche la piega?"\n'
        'Tu: "Certo, aggiungo la piega — cambia un po\' la durata ma ci sta."\n\n'
        "# CONTESTO ATTUALE\n"
        f"Data e ora: {now}\n"
        f"Servizi: {services_str}\n"
        f"Staff in servizio: {staff_str}\n\n"
        "# STRUMENTI\n"
        "Hai gli strumenti: check_availability, get_services, create_customer, book_appointment, list_appointments.\n"
        'Usali quando serve, ma non annunciarli. Dì "un attimo che controllo" e chiamali. Il cliente non deve sapere che esiste uno strumento.\n\n'
        "# CHIUSURA\n"
        'Quando il cliente saluta, chiudi calorosa: "Perfetto, ci vediamo presto! Buona giornata!"'
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
        {
            "type": "function",
            "name": "book_appointment",
            "description": "Prenota un appuntamento per un cliente. Usa dopo aver verificato la disponibilità.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Nome del cliente"},
                    "service_name": {"type": "string", "description": "Nome del servizio"},
                    "staff_name": {"type": "string", "description": "Nome dello staff"},
                    "date": {"type": "string", "description": "Data in formato YYYY-MM-DD"},
                    "time": {"type": "string", "description": "Ora in formato HH:MM"},
                },
                "required": ["customer_name", "service_name", "staff_name", "date", "time"],
            },
        },
        {
            "type": "function",
            "name": "list_appointments",
            "description": "Mostra gli appuntamenti di un cliente",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Nome del cliente"},
                },
                "required": ["customer_name"],
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
                "voice": "marin",
                "instructions": instructions,
                "tools": tools,
                "turn_detection": {
                    "type": "semantic_vad",
                    "eagerness": "low",
                    "create_response": True,
                    "interrupt_response": True,
                },
                "input_audio_transcription": {"model": "gpt-4o-transcribe"},
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
        "services": [{"id": s.get("id"), "name": s.get("service_name"), "duration": s.get("duration_minutes"), "price": float(s.get("price_eur", 0))} for s in services],
        "staff": [{"id": s.get("id"), "name": s.get("full_name")} for s in staff],
    }


class FunctionCallRequest(BaseModel):
    shop_id: str
    function_name: str
    arguments: dict


@router.post("/action")
async def execute_action(body: FunctionCallRequest, request: Request):
    """Proxy function calls from the Realtime API to the booking engine."""
    import logging
    logger = logging.getLogger(__name__)
    app = request.app
    booking = app.state.booking_client
    logger.info("Action: %s args=%s shop=%s", body.function_name, body.arguments, body.shop_id)

    try:
        if body.function_name == "check_availability":
            service_names = body.arguments.get("services", [])
            services_list = await booking.get_services(body.shop_id)
            # Resolve service names to IDs
            svc_ids = []
            for name in service_names:
                nl = name.lower()
                for svc in services_list:
                    if nl in svc.get("service_name", "").lower():
                        svc_ids.append(svc["id"])
                        break
            if not svc_ids:
                return {"slots": [], "message": "Servizio non trovato"}

            date_str = body.arguments.get("date")
            if date_str:
                start = date.fromisoformat(date_str)
            else:
                start = date.today() + timedelta(days=1)
            end = start

            staff_name = body.arguments.get("staff_name")
            staff_id = None
            if staff_name:
                staff_list = await booking.get_staff(body.shop_id)
                nl = staff_name.lower()
                for s in staff_list:
                    if nl in s.get("full_name", "").lower():
                        staff_id = s["id"]
                        break

            result = await booking.check_availability(body.shop_id, svc_ids, start, end, staff_id)
            return result

        elif body.function_name == "get_services":
            services = await booking.get_services(body.shop_id)
            return {"services": [{"name": s.get("service_name"), "duration": s.get("duration_minutes"), "price": float(s.get("price_eur", 0))} for s in services]}

        elif body.function_name == "create_customer":
            name = body.arguments.get("name", "")
            phone = body.arguments.get("phone")
            customer = await booking.create_customer(body.shop_id, name, phone)
            return {"created": True, "name": name, "id": customer.get("id") if customer else None}

        elif body.function_name == "book_appointment":
            # Resolve customer, service, staff by name
            customer_name = body.arguments.get("customer_name", "")
            service_name = body.arguments.get("service_name", "")
            staff_name_arg = body.arguments.get("staff_name", "")
            date_str = body.arguments.get("date", "")
            time_str = body.arguments.get("time", "")

            # Find or create customer
            customers = await booking.find_customers_by_phone(body.shop_id, "")
            customer_id = None
            # Search by name in existing customers
            all_customers_resp = await booking.find_customer_by_name_phone(body.shop_id, customer_name, "")
            if all_customers_resp:
                customer_id = all_customers_resp[0].get("id")
            if not customer_id:
                new_cust = await booking.create_customer(body.shop_id, customer_name)
                customer_id = new_cust.get("id") if new_cust else None

            if not customer_id:
                return {"error": "Impossibile trovare o creare il cliente"}

            # Resolve service
            services_list = await booking.get_services(body.shop_id)
            service_id = None
            for svc in services_list:
                if service_name.lower() in svc.get("service_name", "").lower():
                    service_id = svc["id"]
                    break
            if not service_id:
                return {"error": f"Servizio '{service_name}' non trovato"}

            # Resolve staff
            staff_list = await booking.get_staff(body.shop_id)
            staff_id = None
            for s in staff_list:
                if staff_name_arg.lower() in s.get("full_name", "").lower():
                    staff_id = s["id"]
                    break
            if not staff_id:
                return {"error": f"Staff '{staff_name_arg}' non trovato"}

            # Build start_time
            start_time = f"{date_str}T{time_str}:00+01:00"

            appt = await booking.book_appointment(
                shop_id=body.shop_id,
                customer_id=customer_id,
                service_ids=[service_id],
                staff_id=staff_id,
                start_time=start_time,
            )
            if appt:
                return {"booked": True, "appointment_id": appt.get("id"), "start_time": start_time, "staff": staff_name_arg, "service": service_name}
            return {"error": "Errore nella prenotazione"}

        elif body.function_name == "list_appointments":
            customer_name = body.arguments.get("customer_name", "")
            # Find customer by name
            customers = await booking.find_customer_by_name_phone(body.shop_id, customer_name, "")
            if not customers:
                return {"appointments": [], "message": "Cliente non trovato"}
            customer_id = customers[0].get("id")
            appts = await booking.list_appointments(body.shop_id, customer_id)
            return {"appointments": [{"id": a.get("id"), "start_time": str(a.get("start_time")), "status": a.get("status"), "staff": a.get("staff_name")} for a in appts]}

        else:
            return {"error": f"Unknown function: {body.function_name}"}

    except Exception as e:
        return {"error": str(e)}
