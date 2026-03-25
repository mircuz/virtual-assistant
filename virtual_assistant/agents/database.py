"""
Database utilities for agent operations — Lakebase Autoscaling.

Authentication
--------------
Two auth modes supported (per official Databricks docs):

  A. Native Postgres password (RECOMMENDED — never expires):
     Run notebook cell 2b once with a temporary token.  It creates a
     'assistant_app' Postgres role with a generated password and prints:
       LAKEBASE_USER=assistant_app
       LAKEBASE_PASSWORD=<permanent-password>
     Copy into lakebase.env — done. No refresh needed.

  B. Short-lived OAuth token (1-hour TTL, for initial bootstrap only):
     LAKEBASE_PASSWORD env var — set from local CLI:
       databricks postgres generate-database-credential \
         projects/<id>/branches/<branch>/endpoints/primary \
         -o json | jq -r '.token'

Token generation is attempted automatically (only when LAKEBASE_PASSWORD is blank):
  1. Azure AAD notebook context token (JWT only, Azure Databricks)
  2. Databricks SDK  w.postgres.generate_database_credential()
  3. REST API  POST /api/2.0/postgres/generate-database-credential

Project: demo-assistant-autoscale
Host:    ep-morning-salad-e3uf0lci.database.westus.azuredatabricks.net
DB:      databricks_postgres
Schema:  assistant_mochi

FILE_VERSION = "v9-native-auth-2025"
"""

from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from typing import Any, Generator

import psycopg2
from psycopg2.extras import RealDictCursor

FILE_VERSION = "v9-native-auth-2025"

_token_cache: tuple[str, float] | None = None
_TOKEN_TTL = 55 * 60  # refresh 5 min before server expiry


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _get_databricks_auth() -> tuple[str, str]:
    """Return (host, pat_token) from env vars or Databricks notebook context."""
    host = os.getenv("DATABRICKS_HOST", "").strip().rstrip("/")
    token = os.getenv("DATABRICKS_TOKEN", "").strip()
    if not host or not token:
        try:
            from dbruntime.databricks_repl_context import get_context  # type: ignore
            ctx = get_context()
            if not host:
                host = f"https://{ctx.browserHostName}"
            if not token:
                token = ctx.apiToken
        except Exception:
            pass
    return host, token


def _get_workspace_client():
    """Return a WorkspaceClient using env / notebook context credentials."""
    from databricks.sdk import WorkspaceClient  # type: ignore
    host, token = _get_databricks_auth()
    if host and token:
        return WorkspaceClient(host=host, token=token)
    return WorkspaceClient()


# ---------------------------------------------------------------------------
# Endpoint resolution
# ---------------------------------------------------------------------------

def _resolve_endpoint() -> str:
    """
    Return the full Lakebase Autoscaling endpoint resource path.

    Reads LAKEBASE_ENDPOINT directly. If not set, derives from
    LAKEBASE_PROJECT_ID + LAKEBASE_BRANCH (defaults to 'production') + 'primary'.

    Example: projects/12ce9334-.../branches/br-fancy-fire-.../endpoints/primary
    """
    explicit = os.getenv("LAKEBASE_ENDPOINT", "").strip()
    if explicit:
        return explicit

    project_id = os.getenv("LAKEBASE_PROJECT_ID", "").strip()
    host = os.getenv("LAKEBASE_HOST", "").strip()

    if project_id:
        branch = os.getenv("LAKEBASE_BRANCH", "production").strip()
        return f"projects/{project_id}/branches/{branch}/endpoints/primary"

    raise RuntimeError(
        "Set LAKEBASE_ENDPOINT in your env file.\n"
        "Example: LAKEBASE_ENDPOINT=projects/12ce9334-6393-4636-823f-3672b36702c9/branches/br-fancy-fire-e3ase6k2/endpoints/primary\n"
        "Run:  databricks postgres list-branches projects/<UID>  to find the branch name.\n"
        "Run:  databricks postgres list-endpoints projects/<UID>/branches/<BRANCH>  for the endpoint."
    )


def _candidate_endpoints() -> list[str]:
    """Return the configured endpoint path (LAKEBASE_ENDPOINT), no guessing."""
    return [_resolve_endpoint()]


# ---------------------------------------------------------------------------
# OAuth token generation
# ---------------------------------------------------------------------------

def _generate_via_sdk(endpoint: str) -> str:
    """
    Generate token via databricks-sdk w.postgres.

    Does NOT import from databricks.sdk.service.postgres (that module path
    may not exist in all SDK versions).  Calls the method directly with a
    string argument, which the SDK accepts without needing the type classes.
    """
    w = _get_workspace_client()
    if not hasattr(w, "postgres"):
        raise AttributeError(
            "w.postgres not available in this SDK version. "
            "Run: %pip install --force-reinstall 'databricks-sdk>=0.81.0' "
            "then Detach and Re-attach the cluster."
        )
    cred = w.postgres.generate_database_credential(endpoint=endpoint)
    return cred.token


def _generate_via_rest(endpoint: str, host: str, token: str) -> str:
    """Generate Lakebase OAuth token via POST /api/2.0/postgres/generate-database-credential."""
    import requests  # type: ignore

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(
        f"{host}/api/2.0/postgres/generate-database-credential",
        headers=headers,
        json={"endpoint": endpoint},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    lb_token = data.get("token") or (data.get("credential") or {}).get("token")
    if not lb_token:
        raise RuntimeError(f"No token in response: {list(data.keys())}")
    return lb_token


def _get_notebook_aad_token() -> str | None:
    """
    Return the notebook execution context token if it is a JWT (Azure AAD token).

    Azure Databricks notebooks issue short-lived AAD tokens, not PATs.
    Lakebase (both Provisioned and Autoscaling) accepts the AAD token directly
    as the PostgreSQL password — no separate credential generation needed.
    """
    try:
        from dbruntime.databricks_repl_context import get_context  # type: ignore
        tok = get_context().apiToken
        if tok and tok.startswith("ey"):   # JWT
            return tok
    except Exception:
        pass
    return None


def _generate_lakebase_token() -> str:
    """
    Generate a fresh Lakebase OAuth token.

    Strategy (in order):
      1. Azure AAD notebook token used directly (fastest, no API call needed)
      2. Databricks SDK  w.postgres.generate_database_credential()
      3. REST API  POST /api/2.0/postgres/generate-database-credential
    """
    errors: list[str] = []

    # 1. AAD token from notebook context (Azure Databricks only)
    aad = _get_notebook_aad_token()
    if aad:
        return aad
    errors.append("AAD token: not in a notebook or token is not a JWT")

    endpoint = _resolve_endpoint()

    # 2. SDK w.postgres
    try:
        tok = _generate_via_sdk(endpoint)
        return tok
    except AttributeError as e:
        errors.append(f"SDK w.postgres (not available in this cluster): {e}")
    except Exception as e:
        errors.append(f"SDK w.postgres: {e}")

    # 3. REST API  POST /api/2.0/postgres/generate-database-credential
    host, auth_token = _get_databricks_auth()
    try:
        tok = _generate_via_rest(endpoint, host, auth_token)
        return tok
    except Exception as e:
        errors.append(f"REST: {e}")

    raise RuntimeError(
        f"All token generation methods failed for endpoint '{endpoint}':\n"
        + "\n".join(f"  • {err}" for err in errors)
        + f"\n\n── Fix: generate token from your local terminal ──\n"
        + f"  databricks postgres generate-database-credential \\\n"
        + f"    {endpoint} \\\n"
        + f"    -o json | jq -r '.token'\n\n"
        + "Then set in lakebase.env:  LAKEBASE_PASSWORD=<token>  (valid 1 hour)"
    )


def _resolve_lakebase_password() -> str:
    global _token_cache

    explicit = os.getenv("LAKEBASE_PASSWORD", "").strip()
    if explicit:
        return explicit

    if _token_cache is not None:
        tok, expire_at = _token_cache
        if time.time() < expire_at:
            return tok

    tok = _generate_lakebase_token()
    _token_cache = (tok, time.time() + _TOKEN_TTL)
    return tok


# ---------------------------------------------------------------------------
# Config & connection
# ---------------------------------------------------------------------------

class DatabaseConfig:
    def __init__(self) -> None:
        self.host = _get_env("LAKEBASE_HOST")
        self.port = int(os.getenv("LAKEBASE_PORT", "5432"))
        self.database = _get_env("LAKEBASE_DB")
        self.user = _get_env("LAKEBASE_USER")
        self.password = _resolve_lakebase_password()
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
    _load_env_if_needed()
    global _config
    if _config is None:
        _config = DatabaseConfig()
    return _config


def reset_config() -> None:
    """Force config + token refresh on next call."""
    global _config, _token_cache
    _config = None
    _token_cache = None


@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    config = get_config()
    conn = psycopg2.connect(
        host=config.host,
        port=config.port,
        dbname=config.database,
        user=config.user,
        password=config.password,
        sslmode=config.sslmode,
    )
    try:
        with conn.cursor() as _cur:
            _cur.execute(f"SET search_path TO {config.schema}")
        conn.commit()
        yield conn
    finally:
        conn.close()


def fetch_all(query: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params or [])
            return [dict(row) for row in cursor.fetchall()]


def fetch_one(query: str, params: list[Any] | None = None) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params or [])
            row = cursor.fetchone()
            return dict(row) if row else None


def execute(query: str, params: list[Any] | None = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or [])
            conn.commit()
            return cursor.rowcount


def get_schema() -> str:
    return get_config().schema
