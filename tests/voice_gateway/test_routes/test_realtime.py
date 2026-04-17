"""Tests for voice gateway /realtime/token and /realtime/action endpoints."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
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
            "model": "gpt-realtime",
        }

        with patch("voice_gateway.api.routes.realtime.httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
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

        # Verify the payload sent to OpenAI has the new session config
        sent_json = mock_client_instance.post.call_args.kwargs["json"]
        assert sent_json["model"] == "gpt-realtime"
        assert sent_json["voice"] == "marin"
        assert sent_json["turn_detection"]["type"] == "semantic_vad"
        assert sent_json["input_audio_transcription"]["model"] == "gpt-4o-transcribe"

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
