# Unit & Integration Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add comprehensive unit and integration tests for the booking_engine and voice_gateway modules, achieving high coverage of all routes, queries, models, and the booking client.

**Architecture:** Tests mock external dependencies (Databricks SQL, OpenAI API, httpx) at precise boundaries. Unit tests validate each layer in isolation — models, DB queries, route handlers, HTTP client. Integration tests exercise full request flows through the FastAPI app with mocked DB. pytest-asyncio handles async test functions; `unittest.mock.AsyncMock` patches async callables.

**Tech Stack:** pytest, pytest-asyncio, httpx (FastAPI TestClient), unittest.mock, respx (httpx mock transport)

---

## File Structure

```
tests/
├── conftest.py                          # Shared UUIDs, fake data factories
├── booking_engine/
│   ├── conftest.py                      # Booking engine TestClient + DB mocks
│   ├── test_models.py                   # Pydantic model validation
│   ├── test_connection.py               # _rows_to_dicts, _fetchone_dict, get_table
│   ├── test_queries.py                  # Query functions with mocked DB
│   ├── test_availability_helper.py      # _add_working_days pure function
│   └── test_routes/
│       ├── conftest.py                  # Route-level fixtures (mock queries)
│       ├── test_shops.py               # GET /shops/{id}
│       ├── test_customers.py           # GET+POST /shops/{id}/customers
│       ├── test_services.py            # GET services + staff
│       ├── test_availability.py        # GET /shops/{id}/availability
│       └── test_appointments.py        # POST+GET+PATCH appointments
├── voice_gateway/
│   ├── conftest.py                      # Voice gateway fixtures
│   ├── test_booking_client.py           # BookingClient with mocked httpx
│   └── test_routes/
│       ├── conftest.py                  # TestClient + mock BookingClient
│       └── test_realtime.py             # /token and /action endpoints
└── integration/
    ├── conftest.py                      # Integration fixtures
    └── test_booking_flow.py             # Full booking workflow via API
```

New files: `pytest.ini`, `tests/` directory tree (all files above).

---

### Task 1: Project test infrastructure

**Files:**
- Create: `pytest.ini`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Modify: `requirements.txt` (add test deps)

- [ ] **Step 1: Add test dependencies to requirements.txt**

```
# Testing
pytest>=8.0.0
pytest-asyncio>=0.24.0
httpx>=0.27.0
respx>=0.22.0
```

Append these lines to `/Users/mirco.meazzo/virtual-assistant/requirements.txt`.

- [ ] **Step 2: Create pytest.ini**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 3: Create tests/__init__.py**

Empty file.

- [ ] **Step 4: Create tests/conftest.py with shared fixtures**

```python
"""Shared test fixtures — UUIDs, fake data factories."""
from __future__ import annotations

from datetime import datetime, date, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

ROME = ZoneInfo("Europe/Rome")

# ── Fixed UUIDs for deterministic tests ───────────────────────
SHOP_ID = UUID("a0000000-0000-0000-0000-000000000001")
STAFF_ID_1 = UUID("b0000000-0000-0000-0000-000000000001")
STAFF_ID_2 = UUID("b0000000-0000-0000-0000-000000000002")
SERVICE_ID_1 = UUID("c0000000-0000-0000-0000-000000000001")
SERVICE_ID_2 = UUID("c0000000-0000-0000-0000-000000000002")
CUSTOMER_ID = UUID("d0000000-0000-0000-0000-000000000001")
APPOINTMENT_ID = UUID("e0000000-0000-0000-0000-000000000001")


@pytest.fixture
def fake_shop() -> dict:
    return {
        "id": str(SHOP_ID),
        "name": "Salone Bella",
        "phone_number": "+39 012 345 6789",
        "address": "Via Roma 1, Milano",
        "welcome_message": "Ciao! Benvenuto al Salone Bella!",
        "tone_instructions": "Sii gentile e professionale",
        "personality": "Assistente del salone",
        "special_instructions": None,
        "is_active": True,
    }


@pytest.fixture
def fake_staff_list() -> list[dict]:
    return [
        {"id": str(STAFF_ID_1), "full_name": "Maria Rossi", "role": "stylist", "bio": "Senior stylist"},
        {"id": str(STAFF_ID_2), "full_name": "Luca Bianchi", "role": "barber", "bio": "Expert barber"},
    ]


@pytest.fixture
def fake_services_list() -> list[dict]:
    return [
        {
            "id": str(SERVICE_ID_1),
            "service_name": "Taglio donna",
            "description": "Taglio capelli donna",
            "duration_minutes": 30,
            "price_eur": Decimal("25.00"),
            "category": "Taglio",
        },
        {
            "id": str(SERVICE_ID_2),
            "service_name": "Piega",
            "description": "Piega capelli",
            "duration_minutes": 20,
            "price_eur": Decimal("15.00"),
            "category": "Styling",
        },
    ]


@pytest.fixture
def fake_customer() -> dict:
    return {
        "id": str(CUSTOMER_ID),
        "full_name": "Anna Verdi",
        "preferred_staff_id": None,
        "notes": None,
    }


@pytest.fixture
def fake_appointment() -> dict:
    start = datetime(2026, 4, 1, 10, 0, tzinfo=ROME)
    end = start + timedelta(minutes=30)
    return {
        "id": str(APPOINTMENT_ID),
        "shop_id": str(SHOP_ID),
        "customer_id": str(CUSTOMER_ID),
        "staff_id": str(STAFF_ID_1),
        "staff_name": "Maria Rossi",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "status": "scheduled",
        "services": [
            {
                "service_id": str(SERVICE_ID_1),
                "service_name": "Taglio donna",
                "duration_minutes": 30,
                "price_eur": Decimal("25.00"),
            }
        ],
        "notes": None,
    }
```

- [ ] **Step 5: Install test dependencies**

Run: `pip install -r requirements.txt`

- [ ] **Step 6: Verify pytest discovers empty test suite**

Run: `cd /Users/mirco.meazzo/virtual-assistant && python -m pytest --collect-only`
Expected: `no tests ran` (0 items collected, no errors)

- [ ] **Step 7: Commit**

```bash
git add pytest.ini requirements.txt tests/
git commit -m "test: add test infrastructure with pytest, fixtures, and shared conftest"
```

---

### Task 2: Unit tests for Pydantic models

**Files:**
- Create: `tests/booking_engine/__init__.py`
- Create: `tests/booking_engine/test_models.py`

- [ ] **Step 1: Create tests/booking_engine/__init__.py**

Empty file.

- [ ] **Step 2: Write model validation tests**

```python
"""Unit tests for booking_engine Pydantic models."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from booking_engine.api.models import (
    CreateAppointmentRequest,
    CreateCustomerRequest,
    RescheduleRequest,
    ShopResponse,
    ServiceResponse,
    CustomerResponse,
    AppointmentResponse,
    AvailableSlotResponse,
    AvailabilityResponse,
    AppointmentServiceDetail,
    ErrorResponse,
)


class TestCreateAppointmentRequest:
    def test_valid_request(self):
        req = CreateAppointmentRequest(
            customer_id=uuid4(),
            service_ids=[uuid4()],
            staff_id=uuid4(),
            start_time=datetime(2026, 4, 1, 10, 0),
        )
        assert len(req.service_ids) == 1
        assert req.notes is None

    def test_empty_service_ids_rejected(self):
        with pytest.raises(ValidationError, match="service_ids"):
            CreateAppointmentRequest(
                customer_id=uuid4(),
                service_ids=[],
                staff_id=uuid4(),
                start_time=datetime(2026, 4, 1, 10, 0),
            )

    def test_multiple_services_accepted(self):
        ids = [uuid4(), uuid4(), uuid4()]
        req = CreateAppointmentRequest(
            customer_id=uuid4(),
            service_ids=ids,
            staff_id=uuid4(),
            start_time=datetime(2026, 4, 1, 10, 0),
        )
        assert len(req.service_ids) == 3

    def test_notes_optional(self):
        req = CreateAppointmentRequest(
            customer_id=uuid4(),
            service_ids=[uuid4()],
            staff_id=uuid4(),
            start_time=datetime(2026, 4, 1, 10, 0),
            notes="Prima visita",
        )
        assert req.notes == "Prima visita"


class TestCreateCustomerRequest:
    def test_valid_with_phone(self):
        req = CreateCustomerRequest(full_name="Anna Verdi", phone_number="+39123456789")
        assert req.phone_number == "+39123456789"

    def test_phone_optional(self):
        req = CreateCustomerRequest(full_name="Anna Verdi")
        assert req.phone_number is None

    def test_missing_name_rejected(self):
        with pytest.raises(ValidationError, match="full_name"):
            CreateCustomerRequest()


class TestRescheduleRequest:
    def test_valid_with_staff(self):
        req = RescheduleRequest(
            new_start_time=datetime(2026, 4, 2, 14, 0),
            new_staff_id=uuid4(),
        )
        assert req.new_staff_id is not None

    def test_staff_optional(self):
        req = RescheduleRequest(new_start_time=datetime(2026, 4, 2, 14, 0))
        assert req.new_staff_id is None


class TestShopResponse:
    def test_parses_from_dict(self):
        shop = ShopResponse(
            id=uuid4(), name="Salone", is_active=True,
        )
        assert shop.phone_number is None
        assert shop.is_active is True


class TestServiceResponse:
    def test_decimal_price(self):
        svc = ServiceResponse(
            id=uuid4(),
            service_name="Taglio donna",
            duration_minutes=30,
            price_eur=Decimal("25.50"),
        )
        assert svc.price_eur == Decimal("25.50")


class TestAvailabilityResponse:
    def test_empty_slots(self):
        resp = AvailabilityResponse(slots=[])
        assert resp.slots == []
        assert resp.suggestions is None

    def test_with_suggestions(self):
        slot = AvailableSlotResponse(
            staff_id=uuid4(),
            staff_name="Maria",
            slot_start=datetime(2026, 4, 1, 10, 0),
            slot_end=datetime(2026, 4, 1, 10, 30),
        )
        resp = AvailabilityResponse(slots=[], suggestions=[slot])
        assert len(resp.suggestions) == 1


class TestAppointmentResponse:
    def test_services_default_empty(self):
        appt = AppointmentResponse(
            id=uuid4(),
            customer_id=uuid4(),
            staff_id=uuid4(),
            start_time=datetime(2026, 4, 1, 10, 0),
            end_time=datetime(2026, 4, 1, 10, 30),
            status="scheduled",
        )
        assert appt.services == []


class TestErrorResponse:
    def test_error_fields(self):
        err = ErrorResponse(error="not_found", message="Shop not found")
        assert err.error == "not_found"
```

- [ ] **Step 3: Run tests**

Run: `cd /Users/mirco.meazzo/virtual-assistant && python -m pytest tests/booking_engine/test_models.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/booking_engine/
git commit -m "test: add unit tests for booking_engine Pydantic models"
```

---

### Task 3: Unit tests for DB connection helpers

**Files:**
- Create: `tests/booking_engine/test_connection.py`

- [ ] **Step 1: Write connection helper tests**

```python
"""Unit tests for booking_engine.db.connection helper functions."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from booking_engine.db.connection import _rows_to_dicts, _fetchone_dict, get_table


class TestRowsToDicts:
    def test_empty_result(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        assert _rows_to_dicts(cursor) == []

    def test_single_row(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [("val1", 42)]
        cursor.description = [("col_a",), ("col_b",)]
        result = _rows_to_dicts(cursor)
        assert result == [{"col_a": "val1", "col_b": 42}]

    def test_multiple_rows(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [("a", 1), ("b", 2)]
        cursor.description = [("name",), ("num",)]
        result = _rows_to_dicts(cursor)
        assert len(result) == 2
        assert result[0] == {"name": "a", "num": 1}
        assert result[1] == {"name": "b", "num": 2}

    def test_none_values(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(None, "x")]
        cursor.description = [("a",), ("b",)]
        result = _rows_to_dicts(cursor)
        assert result == [{"a": None, "b": "x"}]


class TestFetchoneDict:
    def test_no_row(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        assert _fetchone_dict(cursor) is None

    def test_one_row(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("hello", 99)
        cursor.description = [("greeting",), ("code",)]
        result = _fetchone_dict(cursor)
        assert result == {"greeting": "hello", "code": 99}


class TestGetTable:
    @patch("booking_engine.db.connection._settings", None)
    def test_no_settings_returns_bare_name(self):
        assert get_table("shops") == "shops"

    def test_with_settings_returns_qualified(self):
        mock_settings = MagicMock()
        mock_settings.table_prefix = "mircom_test.virtual_assistant"
        with patch("booking_engine.db.connection._settings", mock_settings):
            assert get_table("shops") == "mircom_test.virtual_assistant.shops"
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/mirco.meazzo/virtual-assistant && python -m pytest tests/booking_engine/test_connection.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/booking_engine/test_connection.py
git commit -m "test: add unit tests for DB connection helpers"
```

---

### Task 4: Unit tests for availability helper

**Files:**
- Create: `tests/booking_engine/test_availability_helper.py`

- [ ] **Step 1: Write _add_working_days tests**

```python
"""Unit tests for _add_working_days helper in availability route."""
from __future__ import annotations

from datetime import date

from booking_engine.api.routes.availability import _add_working_days


class TestAddWorkingDays:
    def test_add_one_day_midweek(self):
        # Wednesday 2026-04-01 + 1 working day = Thursday 2026-04-02
        result = _add_working_days(date(2026, 4, 1), 1)
        assert result == date(2026, 4, 2)

    def test_add_three_days_midweek(self):
        # Monday 2026-03-30 + 3 = Thursday 2026-04-02
        result = _add_working_days(date(2026, 3, 30), 3)
        assert result == date(2026, 4, 2)

    def test_skips_sunday(self):
        # Saturday 2026-04-04 + 1 working day = Monday 2026-04-06
        result = _add_working_days(date(2026, 4, 4), 1)
        assert result == date(2026, 4, 6)

    def test_friday_plus_one_skips_sunday(self):
        # Friday 2026-04-03 + 1 = Saturday 2026-04-04 (weekday < 6 = True)
        result = _add_working_days(date(2026, 4, 3), 1)
        assert result == date(2026, 4, 4)

    def test_zero_days_returns_start(self):
        result = _add_working_days(date(2026, 4, 1), 0)
        assert result == date(2026, 4, 1)
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/mirco.meazzo/virtual-assistant && python -m pytest tests/booking_engine/test_availability_helper.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/booking_engine/test_availability_helper.py
git commit -m "test: add unit tests for _add_working_days helper"
```

---

### Task 5: Unit tests for DB query functions

**Files:**
- Create: `tests/booking_engine/test_queries.py`

- [ ] **Step 1: Write query tests with mocked execute functions**

```python
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
        # execute_void called for INSERT customer + INSERT/UPDATE phone_contacts
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
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/mirco.meazzo/virtual-assistant && python -m pytest tests/booking_engine/test_queries.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/booking_engine/test_queries.py
git commit -m "test: add unit tests for DB query functions"
```

---

### Task 6: Unit tests for booking engine routes

**Files:**
- Create: `tests/booking_engine/test_routes/__init__.py`
- Create: `tests/booking_engine/test_routes/conftest.py`
- Create: `tests/booking_engine/test_routes/test_shops.py`
- Create: `tests/booking_engine/test_routes/test_customers.py`
- Create: `tests/booking_engine/test_routes/test_services.py`
- Create: `tests/booking_engine/test_routes/test_availability.py`
- Create: `tests/booking_engine/test_routes/test_appointments.py`

- [ ] **Step 1: Create route test __init__.py**

Empty file.

- [ ] **Step 2: Create route conftest with TestClient**

```python
"""Fixtures for booking engine route tests — TestClient with mocked DB."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from booking_engine.api.routes import shops, customers, services, availability, appointments


@pytest.fixture
def app() -> FastAPI:
    """Create a bare FastAPI app with all routers, no lifespan (no real DB)."""
    app = FastAPI()
    app.include_router(shops.router, prefix="/api/v1")
    app.include_router(customers.router, prefix="/api/v1")
    app.include_router(services.router, prefix="/api/v1")
    app.include_router(availability.router, prefix="/api/v1")
    app.include_router(appointments.router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
```

- [ ] **Step 3: Write shop route tests**

```python
"""Tests for GET /api/v1/shops/{shop_id}."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.conftest import SHOP_ID


class TestReadShop:
    def test_returns_shop(self, client, fake_shop):
        with patch("booking_engine.api.routes.shops.get_shop", new_callable=AsyncMock, return_value=fake_shop):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Salone Bella"

    def test_returns_404_when_not_found(self, client):
        with patch("booking_engine.api.routes.shops.get_shop", new_callable=AsyncMock, return_value=None):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}")
        assert resp.status_code == 404
        assert resp.json()["error"] == "shop_not_found"

    def test_invalid_uuid_returns_422(self, client):
        resp = client.get("/api/v1/shops/not-a-uuid")
        assert resp.status_code == 422
```

- [ ] **Step 4: Write customer route tests**

```python
"""Tests for customer lookup and creation routes."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.conftest import SHOP_ID


class TestLookupCustomers:
    def test_search_by_phone(self, client, fake_customer):
        with patch("booking_engine.api.routes.customers.find_customers_by_phone",
                    new_callable=AsyncMock, return_value=[fake_customer]):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/customers", params={"phone": "+39123"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_by_name_and_phone(self, client, fake_customer):
        with patch("booking_engine.api.routes.customers.find_customers_by_name_and_phone",
                    new_callable=AsyncMock, return_value=[fake_customer]):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/customers",
                              params={"phone": "+39123", "name": "Anna"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_no_params_returns_empty(self, client):
        resp = client.get(f"/api/v1/shops/{SHOP_ID}/customers")
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateCustomer:
    def test_creates_customer(self, client, fake_customer):
        with patch("booking_engine.api.routes.customers.create_customer",
                    new_callable=AsyncMock, return_value=fake_customer):
            resp = client.post(
                f"/api/v1/shops/{SHOP_ID}/customers",
                json={"full_name": "Anna Verdi", "phone_number": "+39123"},
            )
        assert resp.status_code == 201
        assert resp.json()["full_name"] == "Anna Verdi"

    def test_missing_name_returns_422(self, client):
        resp = client.post(f"/api/v1/shops/{SHOP_ID}/customers", json={})
        assert resp.status_code == 422
```

- [ ] **Step 5: Write services route tests**

```python
"""Tests for services and staff routes."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.conftest import SHOP_ID, STAFF_ID_1


class TestReadServices:
    def test_returns_services(self, client, fake_services_list):
        with patch("booking_engine.api.routes.services.list_services",
                    new_callable=AsyncMock, return_value=fake_services_list):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/services")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_returns_empty_list(self, client):
        with patch("booking_engine.api.routes.services.list_services",
                    new_callable=AsyncMock, return_value=[]):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/services")
        assert resp.status_code == 200
        assert resp.json() == []


class TestReadStaff:
    def test_returns_staff(self, client, fake_staff_list):
        with patch("booking_engine.api.routes.services.list_staff",
                    new_callable=AsyncMock, return_value=fake_staff_list):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/staff")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestReadStaffServices:
    def test_returns_staff_services(self, client, fake_services_list):
        with patch("booking_engine.api.routes.services.get_staff_services",
                    new_callable=AsyncMock, return_value=fake_services_list):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/staff/{STAFF_ID_1}/services")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
```

- [ ] **Step 6: Write availability route tests**

```python
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
```

- [ ] **Step 7: Write appointment route tests**

```python
"""Tests for appointment CRUD routes."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from booking_engine.db.queries import SlotConflictError
from tests.conftest import SHOP_ID, STAFF_ID_1, SERVICE_ID_1, CUSTOMER_ID, APPOINTMENT_ID


class TestBookAppointment:
    def test_creates_appointment(self, client, fake_appointment):
        with patch("booking_engine.api.routes.appointments.create_appointment",
                    new_callable=AsyncMock, return_value=fake_appointment):
            resp = client.post(
                f"/api/v1/shops/{SHOP_ID}/appointments",
                json={
                    "customer_id": str(CUSTOMER_ID),
                    "service_ids": [str(SERVICE_ID_1)],
                    "staff_id": str(STAFF_ID_1),
                    "start_time": "2026-04-01T10:00:00+02:00",
                },
            )
        assert resp.status_code == 201
        assert resp.json()["status"] == "scheduled"

    def test_conflict_returns_409(self, client):
        with patch("booking_engine.api.routes.appointments.create_appointment",
                    new_callable=AsyncMock, side_effect=SlotConflictError("overlap")):
            resp = client.post(
                f"/api/v1/shops/{SHOP_ID}/appointments",
                json={
                    "customer_id": str(CUSTOMER_ID),
                    "service_ids": [str(SERVICE_ID_1)],
                    "staff_id": str(STAFF_ID_1),
                    "start_time": "2026-04-01T10:00:00+02:00",
                },
            )
        assert resp.status_code == 409
        assert resp.json()["error"] == "slot_taken"


class TestReadAppointments:
    def test_returns_appointments(self, client, fake_appointment):
        with patch("booking_engine.api.routes.appointments.list_appointments",
                    new_callable=AsyncMock, return_value=[fake_appointment]):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/appointments",
                              params={"customer_id": str(CUSTOMER_ID)})
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestCancelAppointment:
    def test_cancels_successfully(self, client, fake_appointment):
        cancelled = {**fake_appointment, "status": "cancelled"}
        with patch("booking_engine.api.routes.appointments.cancel_appointment",
                    new_callable=AsyncMock, return_value=cancelled):
            resp = client.patch(f"/api/v1/shops/{SHOP_ID}/appointments/{APPOINTMENT_ID}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_not_cancellable_returns_409(self, client):
        with patch("booking_engine.api.routes.appointments.cancel_appointment",
                    new_callable=AsyncMock, return_value=None):
            resp = client.patch(f"/api/v1/shops/{SHOP_ID}/appointments/{APPOINTMENT_ID}/cancel")
        assert resp.status_code == 409
        assert resp.json()["error"] == "appointment_not_cancellable"


class TestRescheduleAppointment:
    def test_reschedules_successfully(self, client, fake_appointment):
        rescheduled = {**fake_appointment, "start_time": "2026-04-02T14:00:00+02:00"}
        with patch("booking_engine.api.routes.appointments.reschedule_appointment",
                    new_callable=AsyncMock, return_value=rescheduled):
            resp = client.patch(
                f"/api/v1/shops/{SHOP_ID}/appointments/{APPOINTMENT_ID}/reschedule",
                json={"new_start_time": "2026-04-02T14:00:00+02:00"},
            )
        assert resp.status_code == 200

    def test_not_found_returns_404(self, client):
        with patch("booking_engine.api.routes.appointments.reschedule_appointment",
                    new_callable=AsyncMock, return_value=None):
            resp = client.patch(
                f"/api/v1/shops/{SHOP_ID}/appointments/{APPOINTMENT_ID}/reschedule",
                json={"new_start_time": "2026-04-02T14:00:00+02:00"},
            )
        assert resp.status_code == 404

    def test_conflict_returns_409(self, client):
        with patch("booking_engine.api.routes.appointments.reschedule_appointment",
                    new_callable=AsyncMock, side_effect=SlotConflictError("overlap")):
            resp = client.patch(
                f"/api/v1/shops/{SHOP_ID}/appointments/{APPOINTMENT_ID}/reschedule",
                json={"new_start_time": "2026-04-02T14:00:00+02:00"},
            )
        assert resp.status_code == 409
        assert resp.json()["error"] == "slot_taken"
```

- [ ] **Step 8: Run all route tests**

Run: `cd /Users/mirco.meazzo/virtual-assistant && python -m pytest tests/booking_engine/test_routes/ -v`
Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
git add tests/booking_engine/test_routes/
git commit -m "test: add unit tests for all booking engine routes"
```

---

### Task 7: Unit tests for BookingClient

**Files:**
- Create: `tests/voice_gateway/__init__.py`
- Create: `tests/voice_gateway/conftest.py`
- Create: `tests/voice_gateway/test_booking_client.py`

- [ ] **Step 1: Create __init__.py and conftest**

Empty `tests/voice_gateway/__init__.py`.

`tests/voice_gateway/conftest.py`:

```python
"""Fixtures for voice_gateway tests."""
```

- [ ] **Step 2: Write BookingClient tests using respx**

```python
"""Unit tests for BookingClient with mocked HTTP transport."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

import httpx
import pytest
import respx

from voice_gateway.clients.booking_client import BookingClient

SHOP = UUID("a0000000-0000-0000-0000-000000000001")
STAFF = UUID("b0000000-0000-0000-0000-000000000001")
SVC = UUID("c0000000-0000-0000-0000-000000000001")
CUST = UUID("d0000000-0000-0000-0000-000000000001")
APPT = UUID("e0000000-0000-0000-0000-000000000001")
BASE = "http://test-booking:8000"


@pytest.fixture
async def bc():
    client = BookingClient(base_url=BASE, auth_token="test-token")
    async with client:
        yield client


class TestBookingClientInit:
    def test_normalizes_url_without_scheme(self):
        bc = BookingClient(base_url="example.com")
        assert bc._base == "https://example.com"

    def test_strips_trailing_slash(self):
        bc = BookingClient(base_url="http://example.com/")
        assert bc._base == "http://example.com"


class TestBookingClientContextManager:
    async def test_raises_without_context(self):
        bc = BookingClient()
        with pytest.raises(RuntimeError, match="context manager"):
            _ = bc.client


class TestGetShop:
    @respx.mock
    async def test_returns_shop_on_200(self, bc):
        shop_data = {"id": str(SHOP), "name": "Salone"}
        respx.get(f"{BASE}/api/v1/shops/{SHOP}").mock(
            return_value=httpx.Response(200, json=shop_data)
        )
        result = await bc.get_shop(SHOP)
        assert result == shop_data

    @respx.mock
    async def test_returns_none_on_404(self, bc):
        respx.get(f"{BASE}/api/v1/shops/{SHOP}").mock(
            return_value=httpx.Response(404, json={"error": "not_found"})
        )
        result = await bc.get_shop(SHOP)
        assert result is None


class TestFindCustomersByPhone:
    @respx.mock
    async def test_returns_customers(self, bc):
        customers = [{"id": str(CUST), "full_name": "Anna"}]
        respx.get(f"{BASE}/api/v1/shops/{SHOP}/customers").mock(
            return_value=httpx.Response(200, json=customers)
        )
        result = await bc.find_customers_by_phone(SHOP, "+39123")
        assert len(result) == 1

    @respx.mock
    async def test_returns_empty_on_error(self, bc):
        respx.get(f"{BASE}/api/v1/shops/{SHOP}/customers").mock(
            return_value=httpx.Response(500)
        )
        result = await bc.find_customers_by_phone(SHOP, "+39123")
        assert result == []


class TestCreateCustomer:
    @respx.mock
    async def test_creates_customer(self, bc):
        customer = {"id": str(CUST), "full_name": "Anna"}
        respx.post(f"{BASE}/api/v1/shops/{SHOP}/customers").mock(
            return_value=httpx.Response(201, json=customer)
        )
        result = await bc.create_customer(SHOP, "Anna", "+39123")
        assert result["full_name"] == "Anna"


class TestGetServices:
    @respx.mock
    async def test_returns_services(self, bc):
        services = [{"id": str(SVC), "service_name": "Taglio"}]
        respx.get(f"{BASE}/api/v1/shops/{SHOP}/services").mock(
            return_value=httpx.Response(200, json=services)
        )
        result = await bc.get_services(SHOP)
        assert len(result) == 1


class TestGetStaff:
    @respx.mock
    async def test_returns_staff(self, bc):
        staff = [{"id": str(STAFF), "full_name": "Maria"}]
        respx.get(f"{BASE}/api/v1/shops/{SHOP}/staff").mock(
            return_value=httpx.Response(200, json=staff)
        )
        result = await bc.get_staff(SHOP)
        assert len(result) == 1


class TestCheckAvailability:
    @respx.mock
    async def test_returns_availability(self, bc):
        avail = {"slots": [{"staff_id": str(STAFF), "staff_name": "Maria",
                            "slot_start": "2026-04-01T10:00", "slot_end": "2026-04-01T10:30"}]}
        respx.get(f"{BASE}/api/v1/shops/{SHOP}/availability").mock(
            return_value=httpx.Response(200, json=avail)
        )
        result = await bc.check_availability(SHOP, [SVC], date(2026, 4, 1), date(2026, 4, 1))
        assert len(result["slots"]) == 1

    @respx.mock
    async def test_includes_staff_id_param(self, bc):
        avail = {"slots": []}
        route = respx.get(f"{BASE}/api/v1/shops/{SHOP}/availability").mock(
            return_value=httpx.Response(200, json=avail)
        )
        await bc.check_availability(SHOP, [SVC], date(2026, 4, 1), date(2026, 4, 1), staff_id=STAFF)
        assert "staff_id" in str(route.calls[0].request.url)


class TestBookAppointment:
    @respx.mock
    async def test_books_appointment(self, bc):
        appt = {"id": str(APPT), "status": "scheduled"}
        respx.post(f"{BASE}/api/v1/shops/{SHOP}/appointments").mock(
            return_value=httpx.Response(201, json=appt)
        )
        result = await bc.book_appointment(
            SHOP, CUST, [SVC], STAFF, datetime(2026, 4, 1, 10, 0),
        )
        assert result["status"] == "scheduled"


class TestListAppointments:
    @respx.mock
    async def test_lists_appointments(self, bc):
        appts = [{"id": str(APPT), "status": "scheduled"}]
        respx.get(f"{BASE}/api/v1/shops/{SHOP}/appointments").mock(
            return_value=httpx.Response(200, json=appts)
        )
        result = await bc.list_appointments(SHOP, CUST)
        assert len(result) == 1


class TestCancelAppointment:
    @respx.mock
    async def test_cancels_appointment(self, bc):
        cancelled = {"id": str(APPT), "status": "cancelled"}
        respx.patch(f"{BASE}/api/v1/shops/{SHOP}/appointments/{APPT}/cancel").mock(
            return_value=httpx.Response(200, json=cancelled)
        )
        result = await bc.cancel_appointment(SHOP, APPT)
        assert result["status"] == "cancelled"


class TestRescheduleAppointment:
    @respx.mock
    async def test_reschedules_appointment(self, bc):
        rescheduled = {"id": "new-id", "status": "scheduled"}
        respx.patch(f"{BASE}/api/v1/shops/{SHOP}/appointments/{APPT}/reschedule").mock(
            return_value=httpx.Response(200, json=rescheduled)
        )
        result = await bc.reschedule_appointment(SHOP, APPT, datetime(2026, 4, 2, 14, 0))
        assert result["status"] == "scheduled"

    @respx.mock
    async def test_includes_new_staff_id(self, bc):
        rescheduled = {"id": "new-id", "status": "scheduled"}
        route = respx.patch(f"{BASE}/api/v1/shops/{SHOP}/appointments/{APPT}/reschedule").mock(
            return_value=httpx.Response(200, json=rescheduled)
        )
        await bc.reschedule_appointment(SHOP, APPT, datetime(2026, 4, 2, 14, 0), new_staff_id=STAFF)
        body = route.calls[0].request.content
        assert b"new_staff_id" in body
```

- [ ] **Step 3: Run tests**

Run: `cd /Users/mirco.meazzo/virtual-assistant && python -m pytest tests/voice_gateway/test_booking_client.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/voice_gateway/
git commit -m "test: add unit tests for BookingClient with respx mocks"
```

---

### Task 8: Unit tests for voice gateway realtime routes

**Files:**
- Create: `tests/voice_gateway/test_routes/__init__.py`
- Create: `tests/voice_gateway/test_routes/conftest.py`
- Create: `tests/voice_gateway/test_routes/test_realtime.py`

- [ ] **Step 1: Create __init__.py**

Empty file.

- [ ] **Step 2: Create conftest with mock BookingClient**

```python
"""Fixtures for voice gateway route tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from voice_gateway.api.routes import realtime


@pytest.fixture
def mock_booking() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def app(mock_booking) -> FastAPI:
    app = FastAPI()
    app.state.booking_client = mock_booking
    app.state._openai_key = "test-openai-key"
    app.include_router(realtime.router)
    return app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
```

- [ ] **Step 3: Write realtime route tests**

```python
"""Tests for voice gateway /realtime/token and /realtime/action endpoints."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx

from tests.conftest import SHOP_ID, STAFF_ID_1, SERVICE_ID_1, CUSTOMER_ID, APPOINTMENT_ID


# ── /token ────────────────────────────────────────────────────

class TestGetRealtimeToken:
    def test_returns_token(self, client, mock_booking, fake_shop, fake_services_list, fake_staff_list):
        # Convert Decimal to float for JSON serialization in services
        services_json = []
        for s in fake_services_list:
            svc = {**s}
            if svc.get("price_eur"):
                svc["price_eur"] = float(svc["price_eur"])
            services_json.append(svc)

        mock_booking.get_shop.return_value = fake_shop
        mock_booking.get_services.return_value = services_json
        mock_booking.get_staff.return_value = fake_staff_list

        openai_response = {
            "client_secret": {"value": "ephemeral-token-123", "expires_at": 9999999999},
            "model": "gpt-4o-mini-realtime-preview-2024-12-17",
        }

        with patch("voice_gateway.api.routes.realtime.httpx.AsyncClient") as MockClient:
            mock_resp = AsyncMock()
            mock_resp.json.return_value = openai_response
            mock_resp.raise_for_status = lambda: None
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client_instance

            resp = client.post(f"/api/v1/realtime/token?shop_id={SHOP_ID}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["token"] == "ephemeral-token-123"
        assert data["shop"]["name"] == "Salone Bella"
        assert len(data["services"]) == 2
        assert len(data["staff"]) == 2

    def test_returns_404_shop_not_found(self, client, mock_booking):
        mock_booking.get_shop.return_value = None
        resp = client.post(f"/api/v1/realtime/token?shop_id={SHOP_ID}")
        assert resp.status_code == 404

    def test_returns_500_no_openai_key(self, client, app, mock_booking, fake_shop):
        app.state._openai_key = ""
        mock_booking.get_shop.return_value = fake_shop
        resp = client.post(f"/api/v1/realtime/token?shop_id={SHOP_ID}")
        assert resp.status_code == 500


# ── /action: check_availability ───────────────────────────────

class TestActionCheckAvailability:
    def test_resolves_service_names_to_ids(self, client, mock_booking):
        mock_booking.get_services.return_value = [
            {"id": str(SERVICE_ID_1), "service_name": "Taglio donna", "duration_minutes": 30, "price_eur": 25.0},
        ]
        mock_booking.check_availability.return_value = {
            "slots": [{"staff_id": str(STAFF_ID_1), "staff_name": "Maria",
                        "slot_start": "2026-04-01T10:00", "slot_end": "2026-04-01T10:30"}],
            "suggestions": None,
        }

        resp = client.post("/api/v1/realtime/action", json={
            "shop_id": str(SHOP_ID),
            "function_name": "check_availability",
            "arguments": {"services": ["Taglio"], "date": "2026-04-01"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["slots"]) == 1

    def test_service_not_found_returns_message(self, client, mock_booking):
        mock_booking.get_services.return_value = [
            {"id": str(SERVICE_ID_1), "service_name": "Taglio donna"},
        ]
        resp = client.post("/api/v1/realtime/action", json={
            "shop_id": str(SHOP_ID),
            "function_name": "check_availability",
            "arguments": {"services": ["Massaggio"]},
        })
        assert resp.status_code == 200
        assert "non trovato" in resp.json()["message"]


# ── /action: get_services ─────────────────────────────────────

class TestActionGetServices:
    def test_returns_formatted_services(self, client, mock_booking):
        mock_booking.get_services.return_value = [
            {"service_name": "Taglio donna", "duration_minutes": 30, "price_eur": 25.0},
        ]
        resp = client.post("/api/v1/realtime/action", json={
            "shop_id": str(SHOP_ID),
            "function_name": "get_services",
            "arguments": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["services"]) == 1
        assert data["services"][0]["name"] == "Taglio donna"


# ── /action: create_customer ──────────────────────────────────

class TestActionCreateCustomer:
    def test_creates_customer(self, client, mock_booking):
        mock_booking.create_customer.return_value = {"id": str(CUSTOMER_ID), "full_name": "Marco"}
        resp = client.post("/api/v1/realtime/action", json={
            "shop_id": str(SHOP_ID),
            "function_name": "create_customer",
            "arguments": {"name": "Marco", "phone": "+39555"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] is True
        assert data["name"] == "Marco"


# ── /action: book_appointment ─────────────────────────────────

class TestActionBookAppointment:
    def test_books_appointment_with_existing_customer(self, client, mock_booking):
        mock_booking.find_customers_by_phone.return_value = []
        mock_booking.find_customer_by_name_phone.return_value = [
            {"id": str(CUSTOMER_ID), "full_name": "Anna"}
        ]
        mock_booking.get_services.return_value = [
            {"id": str(SERVICE_ID_1), "service_name": "Taglio donna"},
        ]
        mock_booking.get_staff.return_value = [
            {"id": str(STAFF_ID_1), "full_name": "Maria Rossi"},
        ]
        mock_booking.book_appointment.return_value = {
            "id": str(APPOINTMENT_ID), "status": "scheduled",
        }

        resp = client.post("/api/v1/realtime/action", json={
            "shop_id": str(SHOP_ID),
            "function_name": "book_appointment",
            "arguments": {
                "customer_name": "Anna",
                "service_name": "Taglio",
                "staff_name": "Maria",
                "date": "2026-04-01",
                "time": "10:00",
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["booked"] is True

    def test_service_not_found(self, client, mock_booking):
        mock_booking.find_customers_by_phone.return_value = []
        mock_booking.find_customer_by_name_phone.return_value = [
            {"id": str(CUSTOMER_ID), "full_name": "Anna"}
        ]
        mock_booking.get_services.return_value = []

        resp = client.post("/api/v1/realtime/action", json={
            "shop_id": str(SHOP_ID),
            "function_name": "book_appointment",
            "arguments": {
                "customer_name": "Anna",
                "service_name": "Massaggio",
                "staff_name": "Maria",
                "date": "2026-04-01",
                "time": "10:00",
            },
        })
        assert resp.status_code == 200
        assert "error" in resp.json()


# ── /action: list_appointments ────────────────────────────────

class TestActionListAppointments:
    def test_returns_appointments(self, client, mock_booking):
        mock_booking.find_customer_by_name_phone.return_value = [
            {"id": str(CUSTOMER_ID), "full_name": "Anna"}
        ]
        mock_booking.list_appointments.return_value = [
            {"id": str(APPOINTMENT_ID), "start_time": "2026-04-01T10:00:00",
             "status": "scheduled", "staff_name": "Maria"},
        ]

        resp = client.post("/api/v1/realtime/action", json={
            "shop_id": str(SHOP_ID),
            "function_name": "list_appointments",
            "arguments": {"customer_name": "Anna"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["appointments"]) == 1

    def test_customer_not_found(self, client, mock_booking):
        mock_booking.find_customer_by_name_phone.return_value = []

        resp = client.post("/api/v1/realtime/action", json={
            "shop_id": str(SHOP_ID),
            "function_name": "list_appointments",
            "arguments": {"customer_name": "Ghost"},
        })
        assert resp.status_code == 200
        assert resp.json()["appointments"] == []


# ── /action: unknown function ─────────────────────────────────

class TestActionUnknownFunction:
    def test_returns_error(self, client, mock_booking):
        resp = client.post("/api/v1/realtime/action", json={
            "shop_id": str(SHOP_ID),
            "function_name": "nonexistent_fn",
            "arguments": {},
        })
        assert resp.status_code == 200
        assert "Unknown function" in resp.json()["error"]
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/mirco.meazzo/virtual-assistant && python -m pytest tests/voice_gateway/test_routes/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/voice_gateway/test_routes/
git commit -m "test: add unit tests for voice gateway realtime routes"
```

---

### Task 9: Integration tests — full booking flow

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/conftest.py`
- Create: `tests/integration/test_booking_flow.py`

- [ ] **Step 1: Create __init__.py**

Empty file.

- [ ] **Step 2: Create integration conftest**

```python
"""Integration test fixtures — full FastAPI app with mocked DB layer."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from booking_engine.api.routes import shops, customers, services, availability, appointments

ROME = ZoneInfo("Europe/Rome")
SHOP_ID = UUID("a0000000-0000-0000-0000-000000000001")
STAFF_ID = UUID("b0000000-0000-0000-0000-000000000001")
SVC_ID = UUID("c0000000-0000-0000-0000-000000000001")


class FakeDB:
    """In-memory fake database for integration tests."""

    def __init__(self):
        self.shop = {
            "id": str(SHOP_ID), "name": "Salone Test", "phone_number": "+39000",
            "address": "Via Test", "welcome_message": "Ciao!", "tone_instructions": "",
            "personality": "", "special_instructions": None, "is_active": True,
        }
        self.staff = [
            {"id": str(STAFF_ID), "full_name": "Maria Rossi", "role": "stylist", "bio": ""},
        ]
        self.services = [
            {"id": str(SVC_ID), "service_name": "Taglio donna", "description": "",
             "duration_minutes": 30, "price_eur": Decimal("25.00"), "category": "Taglio"},
        ]
        self.customers: list[dict] = []
        self.appointments: list[dict] = []
        self.appointment_services: list[dict] = []

    def reset(self):
        self.customers.clear()
        self.appointments.clear()
        self.appointment_services.clear()


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture
def app(fake_db) -> FastAPI:
    app = FastAPI()
    app.include_router(shops.router, prefix="/api/v1")
    app.include_router(customers.router, prefix="/api/v1")
    app.include_router(services.router, prefix="/api/v1")
    app.include_router(availability.router, prefix="/api/v1")
    app.include_router(appointments.router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
```

- [ ] **Step 3: Write integration tests**

```python
"""Integration tests — complete booking workflows via the REST API.

These tests exercise multiple routes in sequence, mocking only the DB query
layer to simulate end-to-end API behaviour without Databricks.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

from tests.integration.conftest import SHOP_ID, STAFF_ID, SVC_ID, FakeDB

ROME = ZoneInfo("Europe/Rome")


class TestCustomerCreationAndLookup:
    """Create a customer, then look them up by phone."""

    def test_create_then_lookup(self, client, fake_db):
        cust_id = str(uuid4())
        created = {"id": cust_id, "full_name": "Anna Verdi", "preferred_staff_id": None, "notes": None}

        with patch("booking_engine.api.routes.customers.create_customer",
                    new_callable=AsyncMock, return_value=created):
            resp = client.post(
                f"/api/v1/shops/{SHOP_ID}/customers",
                json={"full_name": "Anna Verdi", "phone_number": "+39123456789"},
            )
        assert resp.status_code == 201
        customer_id = resp.json()["id"]

        with patch("booking_engine.api.routes.customers.find_customers_by_phone",
                    new_callable=AsyncMock, return_value=[created]):
            resp = client.get(
                f"/api/v1/shops/{SHOP_ID}/customers",
                params={"phone": "+39123456789"},
            )
        assert resp.status_code == 200
        assert resp.json()[0]["id"] == customer_id


class TestFullBookingWorkflow:
    """Check services → check availability → book → list → cancel."""

    def test_complete_booking_lifecycle(self, client, fake_db):
        # 1. List services
        with patch("booking_engine.api.routes.services.list_services",
                    new_callable=AsyncMock, return_value=fake_db.services):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/services")
        assert resp.status_code == 200
        services = resp.json()
        assert len(services) == 1
        service_id = services[0]["id"]

        # 2. List staff
        with patch("booking_engine.api.routes.services.list_staff",
                    new_callable=AsyncMock, return_value=fake_db.staff):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/staff")
        assert resp.status_code == 200
        staff = resp.json()
        staff_id = staff[0]["id"]

        # 3. Check availability
        start = datetime(2026, 4, 1, 10, 0, tzinfo=ROME)
        slot = {
            "staff_id": staff_id, "staff_name": "Maria Rossi",
            "slot_start": start.isoformat(),
            "slot_end": (start + timedelta(minutes=30)).isoformat(),
        }
        with patch("booking_engine.api.routes.availability.get_available_slots",
                    new_callable=AsyncMock, return_value=[slot]):
            resp = client.get(
                f"/api/v1/shops/{SHOP_ID}/availability",
                params={
                    "service_ids": service_id,
                    "start_date": "2026-04-01",
                    "end_date": "2026-04-01",
                },
            )
        assert resp.status_code == 200
        slots = resp.json()["slots"]
        assert len(slots) == 1

        # 4. Create customer
        cust_id = str(uuid4())
        cust = {"id": cust_id, "full_name": "Anna Verdi", "preferred_staff_id": None, "notes": None}
        with patch("booking_engine.api.routes.customers.create_customer",
                    new_callable=AsyncMock, return_value=cust):
            resp = client.post(
                f"/api/v1/shops/{SHOP_ID}/customers",
                json={"full_name": "Anna Verdi", "phone_number": "+39123"},
            )
        assert resp.status_code == 201
        customer_id = resp.json()["id"]

        # 5. Book appointment
        appt_id = str(uuid4())
        appt = {
            "id": appt_id, "customer_id": customer_id,
            "staff_id": staff_id, "staff_name": "Maria Rossi",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=30)).isoformat(),
            "status": "scheduled",
            "services": [{"service_id": service_id, "service_name": "Taglio donna",
                          "duration_minutes": 30, "price_eur": Decimal("25.00")}],
            "notes": None,
        }
        with patch("booking_engine.api.routes.appointments.create_appointment",
                    new_callable=AsyncMock, return_value=appt):
            resp = client.post(
                f"/api/v1/shops/{SHOP_ID}/appointments",
                json={
                    "customer_id": customer_id,
                    "service_ids": [service_id],
                    "staff_id": staff_id,
                    "start_time": start.isoformat(),
                },
            )
        assert resp.status_code == 201
        assert resp.json()["status"] == "scheduled"
        appointment_id = resp.json()["id"]

        # 6. List appointments
        with patch("booking_engine.api.routes.appointments.list_appointments",
                    new_callable=AsyncMock, return_value=[appt]):
            resp = client.get(
                f"/api/v1/shops/{SHOP_ID}/appointments",
                params={"customer_id": customer_id},
            )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # 7. Cancel appointment
        cancelled = {**appt, "status": "cancelled"}
        with patch("booking_engine.api.routes.appointments.cancel_appointment",
                    new_callable=AsyncMock, return_value=cancelled):
            resp = client.patch(f"/api/v1/shops/{SHOP_ID}/appointments/{appointment_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"


class TestRescheduleWorkflow:
    """Book → reschedule to new time."""

    def test_book_then_reschedule(self, client, fake_db):
        start = datetime(2026, 4, 1, 10, 0, tzinfo=ROME)
        new_start = datetime(2026, 4, 2, 14, 0, tzinfo=ROME)
        cust_id = str(uuid4())
        appt_id = str(uuid4())

        appt = {
            "id": appt_id, "customer_id": cust_id,
            "staff_id": str(STAFF_ID), "staff_name": "Maria Rossi",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=30)).isoformat(),
            "status": "scheduled",
            "services": [{"service_id": str(SVC_ID), "service_name": "Taglio donna",
                          "duration_minutes": 30, "price_eur": Decimal("25.00")}],
            "notes": None,
        }

        # Book
        with patch("booking_engine.api.routes.appointments.create_appointment",
                    new_callable=AsyncMock, return_value=appt):
            resp = client.post(
                f"/api/v1/shops/{SHOP_ID}/appointments",
                json={
                    "customer_id": cust_id,
                    "service_ids": [str(SVC_ID)],
                    "staff_id": str(STAFF_ID),
                    "start_time": start.isoformat(),
                },
            )
        assert resp.status_code == 201

        # Reschedule
        new_appt_id = str(uuid4())
        rescheduled = {
            **appt,
            "id": new_appt_id,
            "start_time": new_start.isoformat(),
            "end_time": (new_start + timedelta(minutes=30)).isoformat(),
        }
        with patch("booking_engine.api.routes.appointments.reschedule_appointment",
                    new_callable=AsyncMock, return_value=rescheduled):
            resp = client.patch(
                f"/api/v1/shops/{SHOP_ID}/appointments/{appt_id}/reschedule",
                json={"new_start_time": new_start.isoformat()},
            )
        assert resp.status_code == 200
        assert resp.json()["id"] == new_appt_id


class TestSlotConflictHandling:
    """Attempt to double-book the same slot — expect 409."""

    def test_double_booking_returns_409(self, client, fake_db):
        from booking_engine.db.queries import SlotConflictError

        start = datetime(2026, 4, 1, 10, 0, tzinfo=ROME)
        cust_id = str(uuid4())
        appt = {
            "id": str(uuid4()), "customer_id": cust_id,
            "staff_id": str(STAFF_ID), "staff_name": "Maria Rossi",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=30)).isoformat(),
            "status": "scheduled", "services": [], "notes": None,
        }

        # First booking succeeds
        with patch("booking_engine.api.routes.appointments.create_appointment",
                    new_callable=AsyncMock, return_value=appt):
            resp = client.post(
                f"/api/v1/shops/{SHOP_ID}/appointments",
                json={
                    "customer_id": cust_id,
                    "service_ids": [str(SVC_ID)],
                    "staff_id": str(STAFF_ID),
                    "start_time": start.isoformat(),
                },
            )
        assert resp.status_code == 201

        # Second booking conflicts
        with patch("booking_engine.api.routes.appointments.create_appointment",
                    new_callable=AsyncMock, side_effect=SlotConflictError("overlap")):
            resp = client.post(
                f"/api/v1/shops/{SHOP_ID}/appointments",
                json={
                    "customer_id": cust_id,
                    "service_ids": [str(SVC_ID)],
                    "staff_id": str(STAFF_ID),
                    "start_time": start.isoformat(),
                },
            )
        assert resp.status_code == 409
        assert resp.json()["error"] == "slot_taken"


class TestHealthEndpoint:
    """Verify the health endpoint works in isolation."""

    def test_health_returns_ok(self):
        from booking_engine.api.app import create_app
        from unittest.mock import patch, AsyncMock

        with (
            patch("booking_engine.api.app.Settings") as MockSettings,
            patch("booking_engine.api.app.init_connection", new_callable=AsyncMock),
            patch("booking_engine.api.app.close_connection", new_callable=AsyncMock),
        ):
            mock_settings = MockSettings.return_value
            mock_settings.databricks_token = "fake"
            mock_settings.databricks_server_hostname = "host"
            mock_settings.databricks_http_path = "/sql"
            mock_settings.databricks_catalog = "cat"
            mock_settings.databricks_schema = "sch"

            app = create_app()
            with TestClient(app) as tc:
                resp = tc.get("/health")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}
```

- [ ] **Step 4: Run all integration tests**

Run: `cd /Users/mirco.meazzo/virtual-assistant && python -m pytest tests/integration/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/integration/
git commit -m "test: add integration tests for full booking workflow"
```

---

### Task 10: Run full test suite and verify coverage

- [ ] **Step 1: Run the complete test suite**

Run: `cd /Users/mirco.meazzo/virtual-assistant && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS (50+ tests, 0 failures)

- [ ] **Step 2: Run with coverage report**

Run: `pip install pytest-cov && cd /Users/mirco.meazzo/virtual-assistant && python -m pytest tests/ --cov=booking_engine --cov=voice_gateway --cov-report=term-missing -v`
Expected: Coverage report showing >80% line coverage on route handlers, models, and booking client.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "test: complete unit and integration test suite for booking engine and voice gateway"
```
