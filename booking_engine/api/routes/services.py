"""Services and staff routes."""
from uuid import UUID
from fastapi import APIRouter, Depends
from psycopg_pool import AsyncConnectionPool
from booking_engine.api.app import get_pool
from booking_engine.api.models import ServiceResponse, StaffResponse
from booking_engine.db.queries import list_services, list_staff, get_staff_services

router = APIRouter(tags=["services"])

@router.get("/shops/{shop_id}/services", response_model=list[ServiceResponse])
async def read_services(shop_id: UUID, pool: AsyncConnectionPool = Depends(get_pool)):
    return await list_services(pool, shop_id)

@router.get("/shops/{shop_id}/staff", response_model=list[StaffResponse])
async def read_staff(shop_id: UUID, pool: AsyncConnectionPool = Depends(get_pool)):
    return await list_staff(pool, shop_id)

@router.get("/shops/{shop_id}/staff/{staff_id}/services", response_model=list[ServiceResponse])
async def read_staff_services(shop_id: UUID, staff_id: UUID, pool: AsyncConnectionPool = Depends(get_pool)):
    return await get_staff_services(pool, staff_id)
