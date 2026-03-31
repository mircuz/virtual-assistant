"""Live DB test fixtures — real Databricks SQL connection.

These tests run against the actual mircom_test.virtual_assistant schema.
They are skipped automatically if the Databricks connection cannot be established.

Run with: pytest tests/live_db/ -v
"""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

import pytest

from booking_engine.config import Settings
from booking_engine.db import connection

logger = logging.getLogger(__name__)

# ── Seed data IDs from 02_seed_data.sql ───────────────────────
SHOP_ID = UUID("a0000000-0000-0000-0000-000000000001")
SHOP_ID_2 = UUID("b0000000-0000-0000-0000-000000000002")

STAFF_MIRCO = UUID("11111111-0000-0000-0000-000000000001")
STAFF_GIULIA = UUID("11111111-0000-0000-0000-000000000002")
STAFF_MARCO = UUID("11111111-0000-0000-0000-000000000003")

SVC_TAGLIO_DONNA = UUID("aaaa0001-0000-0000-0000-000000000001")  # 45 min, €35
SVC_TAGLIO_UOMO = UUID("aaaa0001-0000-0000-0000-000000000002")   # 30 min, €25
SVC_COLORE = UUID("aaaa0001-0000-0000-0000-000000000003")        # 60 min, €55
SVC_PIEGA = UUID("aaaa0001-0000-0000-0000-000000000005")         # 30 min, €20

CUSTOMER_MARIA = UUID("cccc0001-0000-0000-0000-000000000001")
CUSTOMER_LUCA = UUID("cccc0001-0000-0000-0000-000000000002")

PHONE_MARIA = "+39 333 1111111"
PHONE_LUCA = "+39 333 2222222"


def _get_db_settings() -> Settings:
    """Build Settings for the live DB using the Databricks CLI profile."""
    import subprocess
    import json

    host = "e2-demo-field-eng.cloud.databricks.com"
    http_path = "/sql/1.0/warehouses/03560442e95cb440"

    # Try getting token from databricks CLI
    try:
        result = subprocess.run(
            ["databricks", "auth", "token", "--profile", "e2-demo-field-eng"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            token = data.get("access_token", "")
        else:
            # Fallback: try default profile token from ~/.databrickscfg
            token = ""
    except Exception:
        token = ""

    if not token:
        return None

    return Settings(
        databricks_server_hostname=host,
        databricks_http_path=http_path,
        databricks_token=token,
        databricks_catalog="mircom_test",
        databricks_schema="virtual_assistant",
    )


def _try_connect() -> bool:
    """Attempt a real DB connection. Returns True if successful."""
    settings = _get_db_settings()
    if settings is None:
        return False

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(connection.init_connection(settings))
        # Quick smoke test
        result = loop.run_until_complete(
            connection.execute("SELECT 1 AS ping")
        )
        loop.close()
        return result is not None and len(result) > 0
    except Exception as e:
        logger.warning("Live DB connection failed: %s", e)
        return False


# Try connecting once at import time
_db_available = _try_connect()

# Skip all tests in this directory if DB is unavailable
pytestmark = pytest.mark.skipif(
    not _db_available,
    reason="Databricks SQL connection unavailable (run `databricks auth login --profile e2-demo-field-eng` to authenticate)",
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
    # Teardown: delete test customers and their phone contacts
    if ids:
        loop = asyncio.get_event_loop()
        for cid in ids:
            try:
                loop.run_until_complete(connection.execute_void(
                    f"DELETE FROM {connection.get_table('phone_contacts')} WHERE customer_id = %(cid)s",
                    {"cid": cid},
                ))
                loop.run_until_complete(connection.execute_void(
                    f"DELETE FROM {connection.get_table('customers')} WHERE id = %(cid)s",
                    {"cid": cid},
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
            try:
                loop.run_until_complete(connection.execute_void(
                    f"DELETE FROM {connection.get_table('appointment_services')} WHERE appointment_id = %(aid)s",
                    {"aid": aid},
                ))
                loop.run_until_complete(connection.execute_void(
                    f"DELETE FROM {connection.get_table('appointments')} WHERE id = %(aid)s",
                    {"aid": aid},
                ))
            except Exception as e:
                logger.warning("Cleanup failed for appointment %s: %s", aid, e)
