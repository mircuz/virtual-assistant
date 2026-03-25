"""Shop configuration routes."""
from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from psycopg_pool import AsyncConnectionPool
from booking_engine.api.app import get_pool
from booking_engine.api.models import ShopResponse, ErrorResponse
from booking_engine.db.queries import get_shop

router = APIRouter(tags=["shops"])

@router.get("/shops/{shop_id}", response_model=ShopResponse, responses={404: {"model": ErrorResponse}})
async def read_shop(shop_id: UUID, pool: AsyncConnectionPool = Depends(get_pool)):
    shop = await get_shop(pool, shop_id)
    if not shop:
        return JSONResponse(status_code=404, content={"error": "shop_not_found", "message": f"Shop {shop_id} not found"})
    return shop
