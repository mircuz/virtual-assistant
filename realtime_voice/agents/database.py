"""
Database utilities for agent operations.

Provides PostgreSQL connection management and query helpers
for the Lakebase database.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator

import psycopg2
from psycopg2.extras import RealDictCursor


def _get_env(name: str, default: str | None = None) -> str:
    """Get environment variable or raise if missing."""
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


class DatabaseConfig:
    """Database configuration from environment variables."""
    
    def __init__(self):
        self.host = _get_env("LAKEBASE_HOST")
        self.port = int(os.getenv("LAKEBASE_PORT", "5432"))
        self.database = _get_env("LAKEBASE_DB")
        self.user = _get_env("LAKEBASE_USER")
        self.password = _get_env("LAKEBASE_PASSWORD")
        self.sslmode = os.getenv("LAKEBASE_SSLMODE", "require")
        self.schema = os.getenv("LAKEBASE_SCHEMA", "assistant_mochi")


_config: DatabaseConfig | None = None


def _load_env_if_needed() -> None:
    env_file = os.getenv("ENV_FILE")
    if not env_file:
        volume_base = os.getenv("VOLUME_BASE")
        if volume_base:
            env_file = f"{volume_base.rstrip('/')}/lakebase.env"
    if not env_file:
        return

    try:
        from pathlib import Path

        path = Path(env_file)
        if not path.exists():
            return
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except Exception:
        return


def get_config() -> DatabaseConfig:
    """Get or create database configuration."""
    _load_env_if_needed()
    global _config
    if _config is None:
        _config = DatabaseConfig()
    return _config


@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Get a database connection as a context manager.
    
    Usage:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(...)
    """
    config = get_config()
    conn = psycopg2.connect(
        host=config.host,
        port=config.port,
        dbname=config.database,
        user=config.user,
        password=config.password,
        sslmode=config.sslmode,
        options=f"-c search_path={config.schema}",
    )
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(query: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    """
    Execute a query and return all results as dictionaries.
    
    Args:
        query: SQL query string.
        params: Query parameters.
    
    Returns:
        List of row dictionaries.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params or [])
            return [dict(row) for row in cursor.fetchall()]


def fetch_one(query: str, params: list[Any] | None = None) -> dict[str, Any] | None:
    """
    Execute a query and return the first result.
    
    Args:
        query: SQL query string.
        params: Query parameters.
    
    Returns:
        Row dictionary or None if no results.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params or [])
            row = cursor.fetchone()
            return dict(row) if row else None


def execute(query: str, params: list[Any] | None = None) -> int:
    """
    Execute a query and return the number of affected rows.
    
    Args:
        query: SQL query string.
        params: Query parameters.
    
    Returns:
        Number of affected rows.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or [])
            conn.commit()
            return cursor.rowcount


def get_schema() -> str:
    """Get the configured database schema name."""
    return get_config().schema
