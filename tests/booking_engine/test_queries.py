"""Tests for query functions using mocked DB connections."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID


SHOP_A = UUID("a0000000-0000-0000-0000-000000000001")
STAFF_1 = UUID("11111111-0000-0000-0000-000000000001")
SERVICE_1 = UUID("aaaa0001-0000-0000-0000-000000000001")


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    conn = AsyncMock()
    cursor = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)
    pool.connection.return_value = cm

    conn.execute.return_value = cursor
    cursor.fetchall = AsyncMock(return_value=[])
    cursor.fetchone = AsyncMock(return_value=None)

    return pool, conn, cursor


@pytest.mark.asyncio
async def test_get_shop_returns_dict(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.fetchone = AsyncMock(return_value={"id": SHOP_A, "name": "Salon Bella", "is_active": True})

    from booking_engine.db.queries import get_shop
    result = await get_shop(pool, SHOP_A)
    assert result["name"] == "Salon Bella"


@pytest.mark.asyncio
async def test_get_shop_not_found(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.fetchone = AsyncMock(return_value=None)

    from booking_engine.db.queries import get_shop
    result = await get_shop(pool, SHOP_A)
    assert result is None


@pytest.mark.asyncio
async def test_list_services(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.fetchall = AsyncMock(return_value=[
        {"id": SERVICE_1, "service_name": "Taglio", "duration_minutes": 30},
    ])

    from booking_engine.db.queries import list_services
    result = await list_services(pool, SHOP_A)
    assert len(result) == 1
    assert result[0]["service_name"] == "Taglio"


@pytest.mark.asyncio
async def test_find_customers_by_phone(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.fetchall = AsyncMock(return_value=[
        {"id": UUID("cccc0001-0000-0000-0000-000000000001"), "full_name": "Maria Rossi"},
    ])

    from booking_engine.db.queries import find_customers_by_phone
    result = await find_customers_by_phone(pool, SHOP_A, "+39 333 1111111")
    assert len(result) == 1
    assert result[0]["full_name"] == "Maria Rossi"
