import pytest
from uuid import uuid4
from datetime import datetime, date
from decimal import Decimal


def test_shop_response_serialization():
    from booking_engine.api.models import ShopResponse
    shop = ShopResponse(
        id=uuid4(), name="Salon Bella", phone_number="+39 02 123",
        address="Via Roma", welcome_message="Ciao!", tone_instructions="friendly",
        personality="sunny", special_instructions=None, is_active=True,
    )
    data = shop.model_dump()
    assert data["name"] == "Salon Bella"
    assert data["special_instructions"] is None


def test_available_slot_response():
    from booking_engine.api.models import AvailableSlotResponse
    slot = AvailableSlotResponse(
        staff_id=uuid4(), staff_name="Mirco",
        slot_start=datetime(2026, 3, 30, 10, 0),
        slot_end=datetime(2026, 3, 30, 11, 30),
    )
    assert slot.staff_name == "Mirco"


def test_create_appointment_request_validation():
    from booking_engine.api.models import CreateAppointmentRequest
    req = CreateAppointmentRequest(
        customer_id=uuid4(), service_ids=[uuid4()],
        staff_id=uuid4(), start_time=datetime(2026, 3, 30, 10, 0),
    )
    assert len(req.service_ids) == 1


def test_error_response():
    from booking_engine.api.models import ErrorResponse
    err = ErrorResponse(error="slot_taken", message="Slot already booked")
    assert err.error == "slot_taken"
