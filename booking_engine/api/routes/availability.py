"""Availability check route with suggestion fallback."""
from datetime import date, timedelta
from uuid import UUID
from fastapi import APIRouter, Query
from booking_engine.api.models import AvailabilityResponse
from booking_engine.db.queries import get_available_slots

router = APIRouter(tags=["availability"])

@router.get("/shops/{shop_id}/availability", response_model=AvailabilityResponse)
async def check_availability(shop_id: UUID, service_ids: str = Query(..., description="Comma-separated service UUIDs"), start_date: date = Query(...), end_date: date = Query(...), staff_id: UUID | None = Query(None)):
    parsed_ids = [UUID(sid.strip()) for sid in service_ids.split(",")]
    slots = await get_available_slots(shop_id, parsed_ids, start_date, end_date, staff_id)
    suggestions = None
    if not slots and staff_id:
        fallback_end = _add_working_days(start_date, 3)
        suggestions = await get_available_slots(shop_id, parsed_ids, start_date, fallback_end, staff_id=None)
    return AvailabilityResponse(slots=slots, suggestions=suggestions)

def _add_working_days(start: date, days: int) -> date:
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 6:
            added += 1
    return current
