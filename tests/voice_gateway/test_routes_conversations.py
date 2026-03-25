import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID, uuid4

SHOP_A = UUID("a0000000-0000-0000-0000-000000000001")

MOCK_SHOP = {
    "id": str(SHOP_A), "name": "Salon Bella", "welcome_message": "Ciao!",
    "tone_instructions": "friendly", "personality": "sunny",
    "special_instructions": None, "is_active": True,
}


@pytest.fixture
def app():
    from voice_gateway.api.app import create_app
    application = create_app()
    # Mock all external dependencies
    application.state.booking_client = AsyncMock()
    application.state.booking_client.get_shop = AsyncMock(return_value=MOCK_SHOP)
    application.state.booking_client.get_services = AsyncMock(return_value=[])
    application.state.booking_client.get_staff = AsyncMock(return_value=[])
    application.state.booking_client.find_customers_by_phone = AsyncMock(return_value=[])
    application.state.stt = None
    application.state.tts = None
    application.state.intent_predict = AsyncMock(return_value='{"action": "chitchat", "args": {}, "confidence": 0.9, "topic": "chitchat"}')
    application.state.response_predict = AsyncMock(return_value="Bene grazie! Come posso aiutarti?")
    return application


@pytest.mark.asyncio
async def test_start_conversation(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/conversations/start", json={"shop_id": str(SHOP_A)})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "greeting_text" in data


@pytest.mark.asyncio
async def test_turn_with_text(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Start session
        start_resp = await client.post("/conversations/start", json={"shop_id": str(SHOP_A)})
        session_id = start_resp.json()["session_id"]

        # Send turn
        resp = await client.post(
            f"/conversations/{session_id}/turn",
            json={"text": "Ciao, come stai?"},
        )
    assert resp.status_code == 200
    assert "response_text" in resp.json()


@pytest.mark.asyncio
async def test_end_conversation(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start_resp = await client.post("/conversations/start", json={"shop_id": str(SHOP_A)})
        session_id = start_resp.json()["session_id"]

        resp = await client.delete(f"/conversations/{session_id}")
    assert resp.status_code == 200
