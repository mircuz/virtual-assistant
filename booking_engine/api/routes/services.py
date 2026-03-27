"""Services and staff routes."""
from uuid import UUID
from fastapi import APIRouter
from booking_engine.api.models import ServiceResponse, StaffResponse
from booking_engine.db.queries import list_services, list_staff, get_staff_services

router = APIRouter(tags=["services"])

@router.get("/shops/{shop_id}/services", response_model=list[ServiceResponse])
async def read_services(shop_id: UUID):
    return await list_services(shop_id)

@router.get("/shops/{shop_id}/staff", response_model=list[StaffResponse])
async def read_staff(shop_id: UUID):
    return await list_staff(shop_id)

@router.get("/shops/{shop_id}/staff/{staff_id}/services", response_model=list[ServiceResponse])
async def read_staff_services(shop_id: UUID, staff_id: UUID):
    return await get_staff_services(staff_id)
