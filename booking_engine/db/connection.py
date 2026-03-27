"""Databricks SQL connection management."""
from __future__ import annotations

import asyncio
import logging

from databricks import sql as dbsql

from booking_engine.config import Settings

logger = logging.getLogger(__name__)

_conn = None
_settings: Settings | None = None


def _rows_to_dicts(cursor) -> list[dict]:
    """Fetch all rows and convert to list of dicts."""
    rows = cursor.fetchall()
    if not rows:
        return []
    cols = [desc[0] for desc in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


def _fetchone_dict(cursor) -> dict | None:
    """Fetch one row as dict."""
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [desc[0] for desc in cursor.description]
    return dict(zip(cols, row))


def _get_raw_connection():
    global _conn
    if _conn is None:
        _reconnect()
    return _conn


def _reconnect():
    """Reconnect to Databricks SQL."""
    global _conn
    if _settings is None:
        raise RuntimeError("Connection not initialized. Call init_connection first.")
    logger.info("(Re)connecting to Databricks SQL...")
    try:
        if _conn:
            _conn.close()
    except Exception:
        pass
    _conn = dbsql.connect(
        server_hostname=_settings.databricks_server_hostname,
        http_path=_settings.databricks_http_path,
        access_token=_settings.databricks_token,
    )


def _execute_with_retry(sql: str, params: dict | None, fetch: str):
    """Execute SQL with one retry on connection error."""
    for attempt in range(2):
        try:
            conn = _get_raw_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(sql, parameters=params)
                if fetch == "all":
                    return _rows_to_dicts(cursor) if cursor.description else []
                elif fetch == "one":
                    return _fetchone_dict(cursor) if cursor.description else None
                else:
                    return None
            finally:
                cursor.close()
        except Exception as e:
            if attempt == 0:
                logger.warning("SQL error, reconnecting: %s", e)
                _reconnect()
            else:
                raise


async def execute(sql: str, params: dict | None = None) -> list[dict]:
    """Execute a SQL statement and return all rows as dicts."""
    return await asyncio.to_thread(_execute_with_retry, sql, params, "all")


async def execute_one(sql: str, params: dict | None = None) -> dict | None:
    """Execute a SQL statement and return one row as dict."""
    return await asyncio.to_thread(_execute_with_retry, sql, params, "one")


async def execute_void(sql: str, params: dict | None = None) -> None:
    """Execute a SQL statement that returns nothing."""
    await asyncio.to_thread(_execute_with_retry, sql, params, "void")


async def init_connection(settings: Settings):
    """Initialize the Databricks SQL connection."""
    global _conn, _settings
    _settings = settings

    def _connect():
        global _conn
        _conn = dbsql.connect(
            server_hostname=settings.databricks_server_hostname,
            http_path=settings.databricks_http_path,
            access_token=settings.databricks_token,
        )
        return _conn

    await asyncio.to_thread(_connect)
    logger.info("Databricks SQL connection initialized")
    return _conn


async def close_connection():
    """Close the Databricks SQL connection."""
    global _conn
    if _conn:
        def _close():
            global _conn
            _conn.close()
            _conn = None
        await asyncio.to_thread(_close)


def get_table(name: str) -> str:
    """Return fully qualified table name."""
    if _settings:
        return f"{_settings.table_prefix}.{name}"
    return name
