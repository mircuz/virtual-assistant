"""Async connection pool for Lakebase (PostgreSQL via psycopg v3)."""
from __future__ import annotations

from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

from booking_engine.config import Settings

_pool: AsyncConnectionPool | None = None


async def init_pool(settings: Settings) -> AsyncConnectionPool:
    global _pool
    schema = settings.lakebase_schema

    async def configure_conn(conn):
        await conn.set_autocommit(True)
        await conn.execute(f"SET search_path TO {schema}")
        await conn.set_autocommit(False)

    _pool = AsyncConnectionPool(
        conninfo=settings.dsn,
        min_size=2,
        max_size=10,
        kwargs={"row_factory": dict_row},
        configure=configure_conn,
        open=False,
    )
    await _pool.open()
    return _pool


async def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
