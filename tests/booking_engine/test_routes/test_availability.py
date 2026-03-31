"""Tests for GET /api/v1/shops/{shop_id}/availability."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from tests.conftest import SHOP_ID, STAFF_ID_1, SERVICE_ID_1

ROME = ZoneInfo("Europe/Rome")


class TestCheckAvailability:
    def test_returns_slots(self, client):
        slots = [
            {"staff_id": str(STAFF_ID_1), "staff_name": "Maria",
             "slot_start": datetime(2026, 4, 1, 10, 0, tzinfo=ROME).isoformat(),
             "slot_end": datetime(2026, 4, 1, 10, 30, tzinfo=ROME).isoformat()},
        ]
        with patch("booking_engine.api.routes.availability.get_available_slots",
                    new_callable=AsyncMock, return_value=slots):
            resp = client.get(
                f"/api/v1/shops/{SHOP_ID}/availability",
                params={
                    "service_ids": str(SERVICE_ID_1),
                    "start_date": "2026-04-01",
                    "end_date": "2026-04-01",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["slots"]) == 1
        assert data["suggestions"] is None

    def test_no_slots_with_staff_triggers_suggestions(self, client):
        suggestion = {
            "staff_id": str(STAFF_ID_1), "staff_name": "Maria",
            "slot_start": datetime(2026, 4, 2, 14, 0, tzinfo=ROME).isoformat(),
            "slot_end": datetime(2026, 4, 2, 14, 30, tzinfo=ROME).isoformat(),
        }

        call_count = 0

        async def mock_get_slots(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return []  # no slots for requested staff
            return [suggestion]  # suggestions without staff filter

        with patch("booking_engine.api.routes.availability.get_available_slots",
                    new_callable=AsyncMock, side_effect=mock_get_slots):
            resp = client.get(
                f"/api/v1/shops/{SHOP_ID}/availability",
                params={
                    "service_ids": str(SERVICE_ID_1),
                    "start_date": "2026-04-01",
                    "end_date": "2026-04-01",
                    "staff_id": str(STAFF_ID_1),
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["slots"] == []
        assert len(data["suggestions"]) == 1

    def test_missing_service_ids_returns_422(self, client):
        resp = client.get(
            f"/api/v1/shops/{SHOP_ID}/availability",
            params={"start_date": "2026-04-01", "end_date": "2026-04-01"},
        )
        assert resp.status_code == 422
