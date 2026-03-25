import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from uuid import UUID
from datetime import datetime

SHOP_A = UUID("a0000000-0000-0000-0000-000000000001")
SERVICE_1 = UUID("aaaa0001-0000-0000-0000-000000000001")

@pytest.fixture
def app():
    from booking_engine.api.app import create_app
    application = create_app()
    application.state.pool = AsyncMock()
    return application

@pytest.mark.asyncio
async def test_availability_returns_slots(app):
    mock_slots = [{"staff_id": UUID("11111111-0000-0000-0000-000000000001"), "staff_name": "Mirco", "slot_start": datetime(2026,3,30,10,0), "slot_end": datetime(2026,3,30,10,45)}]
    with patch("booking_engine.api.routes.availability.get_available_slots", new_callable=AsyncMock) as mock:
        mock.return_value = mock_slots
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/shops/{SHOP_A}/availability", params={"service_ids": str(SERVICE_1), "start_date": "2026-03-30", "end_date": "2026-03-30"})
    assert resp.status_code == 200
    assert len(resp.json()["slots"]) == 1
