"""Unit tests for booking_engine.db.queries with mocked DB layer."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from booking_engine.db.queries import (
    SlotConflictError,
    get_shop,
    list_staff,
    list_services,
    find_customers_by_phone,
    create_customer,
    cancel_appointment,
    create_appointment,
    list_appointments,
)

ROME = ZoneInfo("Europe/Rome")
SHOP = UUID("a0000000-0000-0000-0000-000000000001")
STAFF = UUID("b0000000-0000-0000-0000-000000000001")
SVC = UUID("c0000000-0000-0000-0000-000000000001")
CUST = UUID("d0000000-0000-0000-0000-000000000001")
APPT = UUID("e0000000-0000-0000-0000-000000000001")

# Patch targets
_EX = "booking_engine.db.queries.execute"
_EX1 = "booking_engine.db.queries.execute_one"
_EXV = "booking_engine.db.queries.execute_void"
_GT = "booking_engine.db.queries.get_table"


@pytest.fixture(autouse=True)
def _stub_get_table():
    with patch(_GT, side_effect=lambda n: f"test_schema.{n}"):
        yield


class TestGetShop:
    async def test_returns_shop_dict(self):
        row = {"id": str(SHOP), "name": "Salone", "is_active": True}
        with patch(_EX1, new_callable=AsyncMock, return_value=row) as mock:
            result = await get_shop(SHOP)
        assert result == row
        mock.assert_called_once()

    async def test_returns_none_when_not_found(self):
        with patch(_EX1, new_callable=AsyncMock, return_value=None):
            result = await get_shop(SHOP)
        assert result is None


class TestListStaff:
    async def test_returns_staff_list(self):
        rows = [{"id": str(STAFF), "full_name": "Maria", "role": "stylist", "bio": ""}]
        with patch(_EX, new_callable=AsyncMock, return_value=rows):
            result = await list_staff(SHOP)
        assert len(result) == 1
        assert result[0]["full_name"] == "Maria"


class TestListServices:
    async def test_returns_services(self):
        rows = [{"id": str(SVC), "service_name": "Taglio", "duration_minutes": 30, "price_eur": 25.0, "category": "Taglio", "description": None}]
        with patch(_EX, new_callable=AsyncMock, return_value=rows):
            result = await list_services(SHOP)
        assert len(result) == 1


class TestFindCustomersByPhone:
    async def test_returns_matching_customers(self):
        rows = [{"id": str(CUST), "full_name": "Anna", "preferred_staff_id": None, "notes": None}]
        with patch(_EX, new_callable=AsyncMock, return_value=rows):
            result = await find_customers_by_phone(SHOP, "+39123")
        assert len(result) == 1
        assert result[0]["full_name"] == "Anna"

    async def test_returns_empty_when_no_match(self):
        with patch(_EX, new_callable=AsyncMock, return_value=[]):
            result = await find_customers_by_phone(SHOP, "+39000")
        assert result == []


class TestCreateCustomer:
    async def test_creates_customer_with_phone(self):
        customer_row = {"id": "new-id", "full_name": "Marco", "shop_id": str(SHOP)}
        with (
            patch(_EXV, new_callable=AsyncMock) as mock_void,
            patch(_EX1, new_callable=AsyncMock, return_value=customer_row),
        ):
            result = await create_customer(SHOP, "Marco", "+39555")
        assert result["full_name"] == "Marco"
        assert mock_void.call_count >= 1

    async def test_creates_customer_without_phone(self):
        customer_row = {"id": "new-id", "full_name": "Marco", "shop_id": str(SHOP)}
        with (
            patch(_EXV, new_callable=AsyncMock),
            patch(_EX1, new_callable=AsyncMock, return_value=customer_row),
        ):
            result = await create_customer(SHOP, "Marco")
        assert result["full_name"] == "Marco"


class TestCreateAppointment:
    async def test_creates_appointment_successfully(self):
        svc_rows = [{"id": str(SVC), "duration_minutes": 30, "price_eur": 25.0}]
        appt_row = {"id": "new-appt", "status": "scheduled", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T10:30:00"}

        async def mock_execute(sql, params=None):
            if "SUM" in sql or "duration_minutes" in sql:
                return svc_rows
            return []  # no overlap

        with (
            patch(_EX, new_callable=AsyncMock, side_effect=mock_execute),
            patch(_EXV, new_callable=AsyncMock),
            patch(_EX1, new_callable=AsyncMock, return_value=appt_row),
        ):
            start = datetime(2026, 4, 1, 10, 0, tzinfo=ROME)
            result = await create_appointment(SHOP, CUST, STAFF, [SVC], start)
        assert result["status"] == "scheduled"

    async def test_raises_slot_conflict(self):
        svc_rows = [{"id": str(SVC), "duration_minutes": 30, "price_eur": 25.0}]
        overlap_rows = [{"id": "existing-appt"}]

        call_count = 0

        async def mock_execute(sql, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return svc_rows  # service lookup
            return overlap_rows  # overlap check returns existing

        with (
            patch(_EX, new_callable=AsyncMock, side_effect=mock_execute),
            patch(_EXV, new_callable=AsyncMock),
        ):
            start = datetime(2026, 4, 1, 10, 0, tzinfo=ROME)
            with pytest.raises(SlotConflictError):
                await create_appointment(SHOP, CUST, STAFF, [SVC], start)


class TestCancelAppointment:
    async def test_cancels_scheduled_appointment(self):
        existing = {"id": str(APPT), "status": "scheduled"}
        cancelled = {"id": str(APPT), "status": "cancelled"}

        call_count = 0

        async def mock_execute_one(sql, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return existing
            return cancelled

        with (
            patch(_EX1, new_callable=AsyncMock, side_effect=mock_execute_one),
            patch(_EXV, new_callable=AsyncMock),
        ):
            result = await cancel_appointment(SHOP, APPT)
        assert result["status"] == "cancelled"

    async def test_returns_none_when_not_cancellable(self):
        with patch(_EX1, new_callable=AsyncMock, return_value=None):
            result = await cancel_appointment(SHOP, APPT)
        assert result is None


class TestListAppointments:
    async def test_returns_appointments_with_services(self):
        appt_rows = [
            {"id": str(APPT), "shop_id": str(SHOP), "customer_id": str(CUST),
             "staff_id": str(STAFF), "staff_name": "Maria", "start_time": "2026-04-01T10:00:00",
             "end_time": "2026-04-01T10:30:00", "status": "scheduled", "notes": None}
        ]
        svc_rows = [{"service_id": str(SVC), "service_name": "Taglio", "duration_minutes": 30, "price_eur": 25.0}]

        call_count = 0

        async def mock_execute(sql, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return appt_rows
            return svc_rows

        with patch(_EX, new_callable=AsyncMock, side_effect=mock_execute):
            result = await list_appointments(SHOP, CUST)
        assert len(result) == 1
        assert result[0]["services"] == svc_rows
