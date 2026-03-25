import pytest
from uuid import UUID
from unittest.mock import AsyncMock, MagicMock, patch

SHOP_A = UUID("a0000000-0000-0000-0000-000000000001")


def _make_response(status_code, json_data):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


@pytest.mark.asyncio
async def test_get_shop_config():
    shop_data = {
        "id": str(SHOP_A), "name": "Salon Bella", "is_active": True,
        "phone_number": None, "address": None, "welcome_message": "Ciao!",
        "tone_instructions": "friendly", "personality": "sunny",
        "special_instructions": None,
    }
    mock_response = _make_response(200, shop_data)

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get = AsyncMock(return_value=mock_response)
        instance.aclose = AsyncMock()
        MockClient.return_value = instance

        from voice_gateway.clients.booking_client import BookingClient
        client = BookingClient(base_url="http://booking:8000")
        async with client:
            shop = await client.get_shop(SHOP_A)

    assert shop["name"] == "Salon Bella"


@pytest.mark.asyncio
async def test_get_shop_not_found():
    not_found_data = {"error": "shop_not_found", "message": "Not found"}
    mock_response = _make_response(404, not_found_data)

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get = AsyncMock(return_value=mock_response)
        instance.aclose = AsyncMock()
        MockClient.return_value = instance

        from voice_gateway.clients.booking_client import BookingClient
        client = BookingClient(base_url="http://booking:8000")
        async with client:
            shop = await client.get_shop(SHOP_A)

    assert shop is None
