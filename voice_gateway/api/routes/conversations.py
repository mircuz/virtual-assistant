"""Conversation lifecycle routes: start, turn, end."""
from __future__ import annotations

import json
from uuid import UUID

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from voice_gateway.api.models import (
    StartConversationRequest, StartConversationResponse,
    TurnRequest, TurnResponse, EndConversationResponse,
)
from voice_gateway.conversation.prompt_assembler import assemble_system_prompt
from voice_gateway.conversation.agent import ConversationAgent

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/start", response_model=StartConversationResponse)
async def start_conversation(body: StartConversationRequest, request: Request):
    app = request.app
    booking = app.state.booking_client

    # Load shop config
    shop = await booking.get_shop(body.shop_id)
    if not shop:
        return JSONResponse(status_code=404, content={"error": "shop_not_found", "message": "Shop not found"})

    # Build system prompt
    system_prompt = assemble_system_prompt(shop)

    # Load services & staff for intent router
    services = await booking.get_services(body.shop_id)
    staff = await booking.get_staff(body.shop_id)

    # Create session
    mgr = app.state.session_manager
    session_id = mgr.create_session(
        shop_id=body.shop_id,
        shop_config=shop,
        system_prompt=system_prompt,
        caller_phone=body.caller_phone,
    )

    session = mgr.get_session(session_id)
    # Store resolved lists on session for intent routing
    session._services[:] = [s.get("service_name", "") for s in services]
    session._staff[:] = [s.get("full_name", "") for s in staff]
    session._staff_list[:] = staff
    session._services_list[:] = services

    # Greeting — use GPT-Audio for consistent voice
    greeting = shop.get("welcome_message", "Ciao, benvenuto! Come ti chiami?")
    session.add_assistant_turn(greeting)

    greeting_audio = None
    try:
        greeting_audio = await _tts_via_gpt_audio(app, greeting)
    except Exception as e:
        # Fallback to Kokoro
        if app.state.tts:
            greeting_audio = await app.state.tts.synthesize(greeting)

    return StartConversationResponse(
        session_id=session_id,
        greeting_text=greeting,
        greeting_audio=greeting_audio,
    )


@router.post("/{session_id}/turn", response_model=TurnResponse)
async def process_turn(session_id: UUID, body: TurnRequest, request: Request):
    app = request.app
    mgr = app.state.session_manager
    session = mgr.get_session(session_id)

    if not session:
        return JSONResponse(status_code=404, content={"error": "session_not_found", "message": "Session not found"})

    # Get user text: from direct text or STT
    user_text = body.text
    if not user_text and body.audio_base64 and app.state.stt:
        user_text = await app.state.stt.transcribe(body.audio_base64)

    if not user_text:
        return JSONResponse(status_code=400, content={"error": "no_input", "message": "Provide text or audio_base64"})

    session.add_user_turn(user_text)

    # Single LLM call: intent + response
    agent = ConversationAgent(predict_fn=app.state.llm_predict)
    response_text, action, args = await agent.process(
        system_prompt=session.system_prompt,
        history=session.history,
        services=getattr(session, "_services", []),
        staff=getattr(session, "_staff", []),
    )

    # Execute booking action if the LLM requested one
    action_result = None
    if action == "provide_name":
        name = args.get("name", "")
        action_result = await _identify_customer(app, session, name)
        # No follow-up LLM call needed — the initial response is already good
    elif action in ("check_availability", "list_appointments", "book", "cancel", "reschedule"):
        action_result = await _execute_action(app, session, action, args)
        # Follow-up LLM call to incorporate action results into a natural response
        if action_result:
            import json as _json
            session.add_assistant_turn(response_text)
            result_str = _json.dumps(action_result, default=str, ensure_ascii=False)
            session.add_user_turn(f"[SISTEMA: risultato azione {action}: {result_str}]")
            response_text, _, _ = await agent.process(
                system_prompt=session.system_prompt,
                history=session.history,
                services=getattr(session, "_services", []),
                staff=getattr(session, "_staff", []),
            )
    elif action == "ask_service_info":
        action_result = await _execute_action(app, session, action, args)
        # Service list is already known to the LLM from the system prompt
        # No follow-up needed

    session.add_assistant_turn(response_text)

    # TTS (optional)
    response_audio = None
    if app.state.tts:
        response_audio = await app.state.tts.synthesize(response_text)

    return TurnResponse(
        response_text=response_text,
        response_audio=response_audio,
        action_taken=action,
    )


@router.delete("/{session_id}", response_model=EndConversationResponse)
async def end_conversation(session_id: UUID, request: Request):
    mgr = request.app.state.session_manager
    session = mgr.get_session(session_id)

    if not session:
        return JSONResponse(status_code=404, content={"error": "session_not_found", "message": "Session not found"})

    farewell = "Grazie per aver chiamato, a presto!"
    mgr.end_session(session_id)

    return EndConversationResponse(session_id=session_id, farewell=farewell)


async def _execute_action(app, session, action: str, args: dict) -> dict | None:
    """Dispatch action to Booking Engine and return result."""
    booking = app.state.booking_client
    shop_id = session.shop_id

    try:
        if action == "check_availability":
            # Resolve service names to IDs
            service_names = args.get("services", [])
            service_ids = _resolve_service_ids(service_names, getattr(session, "_services_list", []))
            if not service_ids:
                return {"error": "No matching services found"}

            staff_id = _resolve_staff_id(args.get("staff"), getattr(session, "_staff_list", []))
            date_str = args.get("date", args.get("start_date"))

            if date_str:
                from datetime import date as d
                start = d.fromisoformat(date_str)
                end = args.get("end_date", date_str)
                end = d.fromisoformat(end) if isinstance(end, str) else start
            else:
                from datetime import date as d, timedelta
                start = d.today()
                end = start + timedelta(days=3)

            return await booking.check_availability(shop_id, service_ids, start, end, staff_id)

        elif action == "book":
            return await booking.book_appointment(
                shop_id=shop_id,
                customer_id=UUID(args["customer_id"]),
                service_ids=[UUID(s) for s in args["service_ids"]],
                staff_id=UUID(args["staff_id"]),
                start_time=args["start_time"],
            )

        elif action == "cancel":
            return await booking.cancel_appointment(shop_id, UUID(args["appointment_id"]))

        elif action == "reschedule":
            return await booking.reschedule_appointment(
                shop_id, UUID(args["appointment_id"]),
                args["new_start_time"], args.get("new_staff_id"),
            )

        elif action == "list_appointments":
            if session.customer:
                return await booking.list_appointments(shop_id, UUID(session.customer["id"]))
            return {"error": "Customer not identified yet"}

        elif action == "ask_service_info":
            return {"services": getattr(session, "_services_list", [])}

    except Exception as e:
        return {"error": str(e)}

    return None


async def _identify_customer(app, session, name: str) -> dict:
    """Handle customer identification flow per spec:
    1. If caller_phone provided, search by phone in this shop
    2. Match name (case-insensitive first-name prefix)
    3. If multiple matches, return disambiguation list
    4. If no match, create new customer + link phone
    5. Ambiguity guard: skip phone linking if 5+ linked customers and no match
    """
    booking = app.state.booking_client
    shop_id = session.shop_id
    phone = session.caller_phone

    if phone:
        # Get all customers linked to this phone
        phone_customers = await booking.find_customers_by_phone(shop_id, phone)

        # Ambiguity guard: too many linked customers, skip phone matching
        if len(phone_customers) >= 5:
            customer = await booking.create_customer(shop_id, name)
            session.customer = customer
            return {"identified": True, "new_customer": True, "name": name}

        # Try name+phone match
        matches = await booking.find_customer_by_name_phone(shop_id, name, phone)

        if len(matches) == 1:
            session.customer = matches[0]
            return {"identified": True, "name": matches[0].get("full_name", name)}

        if len(matches) > 1:
            names = [m.get("full_name", "") for m in matches]
            return {"identified": False, "disambiguation": names,
                    "message": f"Abbiamo più clienti con quel nome. Sei {' o '.join(names)}?"}

    # No phone or no match: create new customer
    customer = await booking.create_customer(shop_id, name, phone)
    session.customer = customer
    return {"identified": True, "new_customer": True, "name": name}


def _resolve_service_ids(names: list[str], services: list[dict]) -> list:
    """Match service names to IDs (case-insensitive partial match)."""
    from uuid import UUID
    result = []
    for name in names:
        name_lower = name.lower()
        for svc in services:
            if name_lower in svc.get("service_name", "").lower():
                result.append(UUID(svc["id"]) if isinstance(svc["id"], str) else svc["id"])
                break
    return result


def _resolve_staff_id(name: str | None, staff: list[dict]):
    """Match staff name to ID (case-insensitive partial match)."""
    if not name:
        return None
    from uuid import UUID
    name_lower = name.lower()
    for s in staff:
        if name_lower in s.get("full_name", "").lower():
            return UUID(s["id"]) if isinstance(s["id"], str) else s["id"]
    return None


async def _tts_via_gpt_audio(app, text: str) -> str | None:
    """Generate TTS audio using GPT-Audio endpoint. Returns base64 WAV."""
    host = app.state._gpt_audio_host
    token = app.state._gpt_audio_token
    endpoint = app.state._gpt_audio_endpoint
    url = f"https://{host}/serving-endpoints/{endpoint}/invocations"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "messages": [
            {"role": "system", "content": "Ripeti ESATTAMENTE il testo che ti viene dato. Non aggiungere nulla, non modificare nulla. Ripeti solo le parole esatte."},
            {"role": "user", "content": text},
        ],
        "max_tokens": 80,
        "modalities": ["text", "audio"],
        "audio": {"voice": "nova", "format": "wav"},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        audio = data.get("choices", [{}])[0].get("message", {}).get("audio", {}).get("data", "")
        return audio if audio else None
