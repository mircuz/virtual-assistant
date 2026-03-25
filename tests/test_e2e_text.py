"""End-to-end test using text-only mode (no STT/TTS, mocked Booking Engine + LLMs)."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from uuid import UUID

SHOP_A = UUID("a0000000-0000-0000-0000-000000000001")

MOCK_SHOP = {
    "id": str(SHOP_A), "name": "Salon Bella",
    "welcome_message": "Ciao, benvenuto da Salon Bella! Come ti chiami?",
    "tone_instructions": "Amichevole", "personality": "Sei Bella, solare.",
    "special_instructions": None, "is_active": True,
    "phone_number": None, "address": None,
}

MOCK_SERVICES = [
    {"id": "aaaa0001-0000-0000-0000-000000000001", "service_name": "Taglio donna", "duration_minutes": 45},
]

MOCK_STAFF = [
    {"id": "11111111-0000-0000-0000-000000000001", "full_name": "Mirco Meazzo"},
]


@pytest.fixture
def app():
    from voice_gateway.api.app import create_app
    application = create_app()

    # Mock booking client
    bc = AsyncMock()
    bc.get_shop = AsyncMock(return_value=MOCK_SHOP)
    bc.get_services = AsyncMock(return_value=MOCK_SERVICES)
    bc.get_staff = AsyncMock(return_value=MOCK_STAFF)
    bc.find_customers_by_phone = AsyncMock(return_value=[])
    bc.check_availability = AsyncMock(return_value={
        "slots": [{"staff_id": "11111111-0000-0000-0000-000000000001", "staff_name": "Mirco", "slot_start": "2026-03-30T14:00", "slot_end": "2026-03-30T14:45"}],
        "suggestions": None,
    })
    application.state.booking_client = bc

    # Mock LLMs
    application.state.intent_predict = AsyncMock(side_effect=[
        # Turn 1: provide name
        '{"action": "provide_name", "args": {"name": "Maria"}, "confidence": 0.95, "topic": "booking_related"}',
        # Turn 2: check availability
        '{"action": "check_availability", "args": {"services": ["taglio"], "staff": "Mirco", "date": "2026-03-30"}, "confidence": 0.95, "topic": "booking_related"}',
    ])
    application.state.response_predict = AsyncMock(side_effect=[
        "Ciao Maria! Come posso aiutarti?",
        "Mirco è disponibile domani alle 14. Vuoi prenotare?",
    ])

    application.state.stt = None
    application.state.tts = None

    return application


@pytest.mark.asyncio
async def test_full_conversation_flow(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Start
        resp = await client.post("/conversations/start", json={"shop_id": str(SHOP_A)})
        assert resp.status_code == 200
        data = resp.json()
        session_id = data["session_id"]
        assert "Salon Bella" in data["greeting_text"]

        # Turn 1: provide name
        resp = await client.post(f"/conversations/{session_id}/turn", json={"text": "Sono Maria"})
        assert resp.status_code == 200
        assert "Maria" in resp.json()["response_text"]

        # Turn 2: check availability
        resp = await client.post(
            f"/conversations/{session_id}/turn",
            json={"text": "Vorrei un taglio con Mirco domani"},
        )
        assert resp.status_code == 200
        assert "Mirco" in resp.json()["response_text"]

        # End
        resp = await client.delete(f"/conversations/{session_id}")
        assert resp.status_code == 200
