"""Live DB test fixtures — real Neon PostgreSQL connection.

These tests run against the actual Neon database.
They are skipped automatically if DATABASE_URL is not set or connection fails.

Run with: DATABASE_URL=postgresql://... pytest tests/live_db/ -v
"""
from __future__ import annotations

import asyncio
import logging
import os
from uuid import UUID

import pytest

from booking_engine.config import Settings
from booking_engine.db import connection

logger = logging.getLogger(__name__)

# ── Seed data IDs from 02_seed_data.sql (identical to Databricks version) ──
SHOP_ID = UUID("a0000000-0000-0000-0000-000000000001")
SHOP_ID_2 = UUID("b0000000-0000-0000-0000-000000000002")

STAFF_MIRCO = UUID("11111111-0000-0000-0000-000000000001")
STAFF_GIULIA = UUID("11111111-0000-0000-0000-000000000002")
STAFF_MARCO = UUID("11111111-0000-0000-0000-000000000003")

SVC_TAGLIO_DONNA = UUID("aaaa0001-0000-0000-0000-000000000001")  # 45 min
SVC_TAGLIO_UOMO = UUID("aaaa0001-0000-0000-0000-000000000002")   # 30 min
SVC_COLORE = UUID("aaaa0001-0000-0000-0000-000000000003")        # 60 min
SVC_PIEGA = UUID("aaaa0001-0000-0000-0000-000000000005")         # 30 min

CUSTOMER_MARIA = UUID("cccc0001-0000-0000-0000-000000000001")
CUSTOMER_LUCA = UUID("cccc0001-0000-0000-0000-000000000002")

PHONE_MARIA = "+39 333 1111111"
PHONE_LUCA = "+39 333 2222222"


def _get_db_settings() -> Settings | None:
    """Build Settings from DATABASE_URL environment variable."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return None
    return Settings(database_url=db_url)


def _try_connect() -> bool:
    """Attempt a real DB connection. Returns True if successful."""
    settings = _get_db_settings()
    if settings is None:
        return False
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(connection.init_connection(settings))
        result = loop.run_until_complete(
            connection.execute("SELECT 1 AS ping")
        )
        loop.close()
        return result is not None and len(result) > 0
    except Exception as e:
        logger.warning("Live DB connection failed: %s", e)
        return False


_db_available = _try_connect()

pytestmark = pytest.mark.skipif(
    not _db_available,
    reason="Neon PostgreSQL connection unavailable (set DATABASE_URL env var)",
)


@pytest.fixture(scope="session")
def db_connection():
    """Ensure we have an active DB connection for the test session."""
    if not _db_available:
        pytest.skip("No DB connection")
    yield connection


@pytest.fixture
def cleanup_customer_ids():
    """Collect customer IDs created during tests for cleanup."""
    ids: list[str] = []
    yield ids
    if ids:
        loop = asyncio.get_event_loop()
        for cid in ids:
            uid = UUID(cid) if isinstance(cid, str) else cid
            try:
                loop.run_until_complete(connection.execute_void(
                    "DELETE FROM phone_contacts WHERE customer_id = $1", uid,
                ))
                loop.run_until_complete(connection.execute_void(
                    "DELETE FROM customers WHERE id = $1", uid,
                ))
            except Exception as e:
                logger.warning("Cleanup failed for customer %s: %s", cid, e)


@pytest.fixture
def cleanup_appointment_ids():
    """Collect appointment IDs created during tests for cleanup."""
    ids: list[str] = []
    yield ids
    if ids:
        loop = asyncio.get_event_loop()
        for aid in ids:
            uid = UUID(aid) if isinstance(aid, str) else aid
            try:
                loop.run_until_complete(connection.execute_void(
                    "DELETE FROM appointment_services WHERE appointment_id = $1", uid,
                ))
                loop.run_until_complete(connection.execute_void(
                    "DELETE FROM appointments WHERE id = $1", uid,
                ))
            except Exception as e:
                logger.warning("Cleanup failed for appointment %s: %s", aid, e)
