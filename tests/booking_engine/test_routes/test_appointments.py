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
