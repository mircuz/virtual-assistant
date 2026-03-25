"""Customer lookup and creation routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from psycopg_pool import AsyncConnectionPool
from booking_engine.api.app import get_pool
from booking_engine.api.models import CustomerResponse, CreateCustomerRequest
from booking_engine.db.queries import find_customers_by_phone, find_customers_by_name_and_phone, create_customer

router = APIRouter(tags=["customers"])

@router.get("/shops/{shop_id}/customers", response_model=list[CustomerResponse])
async def lookup_customers(shop_id: UUID, phone: str | None = Query(None), name: str | None = Query(None), pool: AsyncConnectionPool = Depends(get_pool)):
    if phone and name:
        return await find_customers_by_name_and_phone(pool, shop_id, name, phone)
    elif phone:
        return await find_customers_by_phone(pool, shop_id, phone)
    return []

@router.post("/shops/{shop_id}/customers", response_model=CustomerResponse, status_code=201)
async def create_new_customer(shop_id: UUID, body: CreateCustomerRequest, pool: AsyncConnectionPool = Depends(get_pool)):
    return await create_customer(pool, shop_id, body.full_name, body.phone_number)
