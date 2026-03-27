"""Shop configuration routes."""
from uuid import UUID
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from booking_engine.api.models import ShopResponse, ErrorResponse
from booking_engine.db.queries import get_shop

router = APIRouter(tags=["shops"])

@router.get("/shops/{shop_id}", response_model=ShopResponse, responses={404: {"model": ErrorResponse}})
async def read_shop(shop_id: UUID):
    shop = await get_shop(shop_id)
    if not shop:
        return JSONResponse(status_code=404, content={"error": "shop_not_found", "message": f"Shop {shop_id} not found"})
    return shop
