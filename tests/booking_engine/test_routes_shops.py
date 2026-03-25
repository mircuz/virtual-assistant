import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from uuid import UUID

SHOP_A = UUID("a0000000-0000-0000-0000-000000000001")
MOCK_SHOP = {"id": SHOP_A, "name": "Salon Bella", "phone_number": "+39 02 123", "address": "Via Roma", "welcome_message": "Ciao!", "tone_instructions": "friendly", "personality": "sunny", "special_instructions": None, "is_active": True}

@pytest.fixture
def app():
    from booking_engine.api.app import create_app
    application = create_app()
    application.state.pool = AsyncMock()
    return application

@pytest.mark.asyncio
async def test_get_shop_success(app):
    with patch("booking_engine.api.routes.shops.get_shop", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_SHOP
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/shops/{SHOP_A}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Salon Bella"

@pytest.mark.asyncio
async def test_get_shop_not_found(app):
    with patch("booking_engine.api.routes.shops.get_shop", new_callable=AsyncMock) as mock:
        mock.return_value = None
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/shops/{SHOP_A}")
        assert resp.status_code == 404
        assert resp.json()["error"] == "shop_not_found"
