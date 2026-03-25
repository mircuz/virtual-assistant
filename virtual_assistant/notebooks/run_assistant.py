# Databricks notebook source
# MAGIC %md
# MAGIC # Virtual Assistant — Business-Configurable
# MAGIC
# MAGIC **New flow:**
# MAGIC 1. Configure your business (name, type, services, language, tone)
# MAGIC 2. The AI generates a tailored system prompt for your business
# MAGIC 3. Start the conversation
# MAGIC
# MAGIC Works for any business: hair salon, restaurant, dental clinic, gym, spa, and more.

# COMMAND ----------
# Verify required packages are available.
# All deps are declared in requirements.txt — install once per cluster/environment:
#   %pip install -r /Workspace/Users/mirco.meazzo@databricks.com/VirtualAssistant/requirements.txt
# (Run that line in a temporary cell, then detach & re-attach, then delete it.)
_REQUIRED = [
    ("psycopg2", "psycopg2-binary>=2.9.0"),
    ("nest_asyncio", "nest_asyncio>=1.6.0"),
    ("requests", "requests>=2.28.0"),
    ("fastapi", "fastapi>=0.110.0"),
    ("pydantic", "pydantic>=2.0.0"),
    ("databricks.sdk", "databricks-sdk>=0.81.0"),
]
_missing = []
for _mod, _pkg in _REQUIRED:
    try:
        __import__(_mod)
    except ImportError:
        _missing.append(_pkg)

if _missing:
    raise ImportError(
        "Missing packages. Run in a new cell, then detach & re-attach the cluster:\n\n"
        "  %pip install " + " ".join(f'"{p}"' for p in _missing) + "\n\n"
        "Or install everything at once:\n"
        "  %pip install -r /Workspace/Users/mirco.meazzo@databricks.com/VirtualAssistant/requirements.txt"
    )
print("All required packages available ✓")

# COMMAND ----------
# Purge stale .pyc bytecode so the freshly synced source files are always used.
# This prevents "old code still running" bugs after a Workspace sync.
import shutil, pathlib

_REPO_ROOT = pathlib.Path("/Workspace/Users/mirco.meazzo@databricks.com/VirtualAssistant")
_purged = 0
for _cache_dir in _REPO_ROOT.rglob("__pycache__"):
    shutil.rmtree(_cache_dir, ignore_errors=True)
    _purged += 1
print(f"Purged {_purged} __pycache__ directories under {_REPO_ROOT}")

# Also drop any already-imported virtual_assistant modules so Python re-reads the source
import sys
_dropped = [k for k in list(sys.modules) if k.startswith("virtual_assistant")]
for _mod in _dropped:
    del sys.modules[_mod]
if _dropped:
    print(f"Dropped {len(_dropped)} cached module(s): {_dropped[:5]}{'…' if len(_dropped) > 5 else ''}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Configuration

# COMMAND ----------
import os
import sys

# Databricks notebooks run inside an existing event loop (Jupyter/IPython).
# nest_asyncio patches it so asyncio.run() works normally inside the notebook.
import nest_asyncio
nest_asyncio.apply()

# --- Env / secrets ---
dbutils.widgets.text("ENV_FILE", "/Volumes/mircom_test/assistant_mochi/data/lakebase.env", "Env file path (Volume)")
dbutils.widgets.text("VOLUME_BASE", "/Volumes/mircom_test/assistant_mochi/data", "Volume base path")

# --- Business config ---
dbutils.widgets.text("BUSINESS_NAME", "Salon Bella", "Business name")
dbutils.widgets.dropdown(
    "BUSINESS_TYPE", "hair_salon",
    ["hair_salon", "restaurant", "dental_clinic", "medical_clinic", "spa", "gym", "general"],
    "Business type"
)
dbutils.widgets.text("SERVICES", "taglio, colore, piega, trattamenti", "Services (comma-separated)")
dbutils.widgets.dropdown("LANGUAGE", "it", ["it", "en", "es", "fr", "de"], "Language")
dbutils.widgets.dropdown("TONE", "friendly", ["friendly", "professional", "formal"], "Tone")
dbutils.widgets.text("SPECIAL_INSTRUCTIONS", "", "Special instructions (optional)")

# --- Voice ---
dbutils.widgets.dropdown("ENABLE_TTS", "false", ["true", "false"], "Enable TTS")
dbutils.widgets.text("USER_MESSAGE", "", "💬 Your message (re-run this cell to send)")

# Read widget values
env_file     = dbutils.widgets.get("ENV_FILE").strip()
volume_base  = dbutils.widgets.get("VOLUME_BASE").strip()
business_name = dbutils.widgets.get("BUSINESS_NAME").strip()
business_type = dbutils.widgets.get("BUSINESS_TYPE").strip()
services_raw  = dbutils.widgets.get("SERVICES").strip()
language      = dbutils.widgets.get("LANGUAGE").strip()
tone          = dbutils.widgets.get("TONE").strip()
special_instr = dbutils.widgets.get("SPECIAL_INSTRUCTIONS").strip() or None
enable_tts    = dbutils.widgets.get("ENABLE_TTS").strip().lower() == "true"

services = [s.strip() for s in services_raw.split(",") if s.strip()]

print(f"Business : {business_name} ({business_type})")
print(f"Services : {services}")
print(f"Language : {language} | Tone: {tone}")
print(f"TTS      : {enable_tts}")
print(f"Env file : {env_file}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Load Environment Variables

# COMMAND ----------
from pathlib import Path

def load_env(path: str) -> None:
    p = Path(path)
    if not p.exists():
        print(f"WARNING: env file not found at {path}")
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")

if env_file:
    load_env(env_file)
    print("Environment loaded from:", env_file)
elif volume_base:
    load_env(f"{volume_base.rstrip('/')}/lakebase.env")

# Auto-fill Databricks token from notebook context if not set
if not os.getenv("DATABRICKS_TOKEN"):
    try:
        from dbruntime.databricks_repl_context import get_context
        os.environ["DATABRICKS_TOKEN"] = get_context().apiToken
        print("Databricks token: loaded from notebook context")
    except Exception:
        print("WARNING: DATABRICKS_TOKEN not set and notebook context unavailable")

# Auto-fill Databricks host if not set
if not os.getenv("DATABRICKS_HOST"):
    try:
        from dbruntime.databricks_repl_context import get_context
        os.environ["DATABRICKS_HOST"] = f"https://{get_context().browserHostName}"
        print("Databricks host:", os.environ["DATABRICKS_HOST"])
    except Exception:
        print("WARNING: DATABRICKS_HOST not set")

print("\nConfig summary:")
print(f"  DATABRICKS_HOST      = {os.getenv('DATABRICKS_HOST', 'NOT SET')}")
print(f"  DATABRICKS_ENDPOINT  = {os.getenv('DATABRICKS_ENDPOINT', 'NOT SET')}")
print(f"  LAKEBASE_PROJECT_ID  = {os.getenv('LAKEBASE_PROJECT_ID', 'NOT SET')}")
print(f"  LAKEBASE_ENDPOINT    = {os.getenv('LAKEBASE_ENDPOINT', 'NOT SET')}")
print(f"  LAKEBASE_HOST        = {os.getenv('LAKEBASE_HOST', 'NOT SET (run setup cell below)')}")
print(f"  LAKEBASE_USER        = {os.getenv('LAKEBASE_USER', 'NOT SET')}")

# Reset any cached DB config so the next connection picks up the freshly loaded env vars
try:
    from virtual_assistant.agents.database import reset_config
    reset_config()
except ImportError:
    pass  # package not on sys.path yet — will be added in the next cell

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2b. Lakebase — Schema Bootstrap
# MAGIC
# MAGIC Project **demo-assistant-autoscale** is already running.
# MAGIC This cell:
# MAGIC 1. Generates a fresh OAuth token (REST → LAKEBASE_PASSWORD fallback)
# MAGIC 2. Connects to `databricks_postgres`
# MAGIC 3. Creates the `assistant_mochi` schema and applies the hair-salon tables
# MAGIC
# MAGIC **Prerequisites:** `LAKEBASE_HOST` must be set in the env.
# MAGIC If `LAKEBASE_PASSWORD` is blank, the cell tries the REST credential API.
# MAGIC To set a token manually from your terminal:
# MAGIC ```
# MAGIC databricks postgres generate-database-credential \
# MAGIC   projects/demo-assistant-autoscale/branches/production/endpoints/ep-primary \
# MAGIC   -o json | jq -r '.token'
# MAGIC ```

# COMMAND ----------
import psycopg2 as _pg2, requests as _req
from pathlib import Path as _Path

_lb_host     = os.getenv("LAKEBASE_HOST", "").strip()
_lb_port     = int(os.getenv("LAKEBASE_PORT", "5432"))
_lb_db       = os.getenv("LAKEBASE_DB", "databricks_postgres")
_lb_user     = os.getenv("LAKEBASE_USER", "")
_lb_password = os.getenv("LAKEBASE_PASSWORD", "").strip()
_lb_schema   = os.getenv("LAKEBASE_SCHEMA", "assistant_mochi")
_project_id  = os.getenv("LAKEBASE_PROJECT_ID", "12ce9334-6393-4636-823f-3672b36702c9")
_branch_id   = os.getenv("LAKEBASE_BRANCH", "br-fancy-fire-e3ase6k2")
_db_host     = os.getenv("DATABRICKS_HOST", "").strip().rstrip("/")

# Get user from SDK if LAKEBASE_USER not set
if not _lb_user:
    try:
        from databricks.sdk import WorkspaceClient as _WC
        _lb_user = _WC().current_user.me().user_name
        os.environ["LAKEBASE_USER"] = _lb_user
    except Exception:
        raise RuntimeError("Set LAKEBASE_USER in lakebase.env (your Databricks email)")

print(f"Host   : {_lb_host}")
print(f"DB     : {_lb_db}")
print(f"User   : {_lb_user}")
print(f"Schema : {_lb_schema}")

if not _lb_host:
    raise RuntimeError(
        "LAKEBASE_HOST is not set.\n"
        "It should be: ep-morning-salad-e3uf0lci.database.westus.azuredatabricks.net\n"
        "Check that lakebase.env was uploaded to the Volume and re-run cell 2a."
    )

# ── Generate OAuth token if not provided ──────────────────────────────────────
if not _lb_password:
    print("\nLAKEBASE_PASSWORD not set — trying REST credential generation...")
    _db_token = os.getenv("DATABRICKS_TOKEN", "").strip()
    if not _db_token:
        try:
            from dbruntime.databricks_repl_context import get_context as _gctx
            _db_token = _gctx().apiToken
        except Exception:
            pass

    _hdrs = {"Authorization": f"Bearer {_db_token}", "Content-Type": "application/json"}

    # Use the explicit endpoint path from env, falling back to "primary"
    _explicit_ep = os.getenv("LAKEBASE_ENDPOINT", "").strip()
    if _explicit_ep:
        _ep_name = _explicit_ep.split("/")[-1]  # last segment = endpoint ID
    else:
        _ep_name = "primary"
    _ep_candidates = [_ep_name]

    for _ep_name in _ep_candidates:
        _ep_path = f"projects/{_project_id}/branches/{_branch_id}/endpoints/{_ep_name}"
        _r = _req.post(
            f"{_db_host}/api/2.0/postgres/generate-database-credential",
            headers=_hdrs, json={"endpoint": _ep_path}, timeout=30,
        )
        print(f"  endpoint={_ep_name}: HTTP {_r.status_code}" + (f" {_r.text[:80]}" if _r.status_code != 200 else ""))
        if _r.status_code == 200:
            _d = _r.json()
            _lb_password = _d.get("token") or (_d.get("credential") or {}).get("token", "")
            if _lb_password:
                print(f"  ✓ Token ({len(_lb_password)} chars)")
                os.environ["LAKEBASE_ENDPOINT"] = _ep_path
                break

    if not _lb_password:
        _actual_ep = _ep_candidates[0] if _ep_candidates else "ep-morning-salad-e3uf0lci"
        raise RuntimeError(
            "Could not generate an OAuth token from the notebook.\n\n"
            "Run from your local terminal (requires CLI >= 0.285.0):\n"
            f"  brew upgrade databricks   # upgrade if below 0.285.0\n"
            f"  # Discover the exact endpoint name:\n"
            f"  databricks postgres list-endpoints \\\n"
            f"    projects/{_project_id}/branches/production -o json | jq '.[].name'\n\n"
            f"  # Generate token (replace ENDPOINT_NAME with the value above):\n"
            f"  databricks postgres generate-database-credential \\\n"
            f"    projects/{_project_id}/branches/{_branch_id}/endpoints/ENDPOINT_NAME \\\n"
            f"    -o json | jq -r '.token'\n\n"
            "Then set in lakebase.env:  LAKEBASE_PASSWORD=<token>  (valid 1 hour)\n"
            "Also set:                  LAKEBASE_ENDPOINT=projects/{_project_id}/branches/production/endpoints/ENDPOINT_NAME\n"
            "and re-run the env-loading cell (2a) before this one."
        )
else:
    print(f"\nUsing LAKEBASE_PASSWORD from env ({len(_lb_password)} chars)")

# ── Connect ───────────────────────────────────────────────────────────────────
print("\nConnecting to Lakebase Autoscaling...")
_ENDPOINT_PATH = f"projects/{_project_id}/branches/{_branch_id}/endpoints/primary"

try:
    _conn = _pg2.connect(
        host=_lb_host, port=_lb_port, dbname=_lb_db,
        user=_lb_user, password=_lb_password, sslmode="require",
    )
except Exception as _conn_err:
    _err_msg = str(_conn_err).lower()
    if "password authentication failed" in _err_msg or "authentication failed" in _err_msg:
        raise RuntimeError(
            "Authentication failed — your LAKEBASE_PASSWORD token has expired (OAuth tokens last 1 hour).\n\n"
            "Generate a fresh token from your LOCAL terminal:\n\n"
            f"  TOKEN=$(databricks postgres generate-database-credential \\\n"
            f"    {_ENDPOINT_PATH} \\\n"
            f"    -o json | jq -r '.token')\n"
            f"  echo \"LAKEBASE_PASSWORD=$TOKEN\"\n\n"
            "Then:\n"
            "  1. Copy the printed LAKEBASE_PASSWORD=<token> line into lakebase.env\n"
            "  2. Upload lakebase.env to the Volume\n"
            "  3. Re-run cell 2a (Load Environment Variables)\n"
            "  4. Re-run this cell\n\n"
            "After this cell succeeds, it will print permanent credentials that NEVER expire.\n"
            "Copy those into lakebase.env and you will never need to rotate again."
        ) from None
    raise

_conn.autocommit = True
_cur = _conn.cursor()
_cur.execute("SELECT version()")
print(f"✓ Connected — PG {_cur.fetchone()[0][:50]}...")

# ── Create schema + apply DDL (requires admin/owner role) ─────────────────────
# The 'authenticator' role cannot CREATE schemas — that needs a Databricks admin
# user. Run the block below from your LOCAL terminal ONCE, then this cell only
# verifies the schema exists and skips DDL.
_BOOTSTRAP_CMD = f"""
  HOST={_lb_host}
  TOKEN=$(databricks postgres generate-database-credential \\
    {_ENDPOINT_PATH} -o json | jq -r '.token')
  EMAIL=mirco.meazzo@databricks.com

  PGPASSWORD=$TOKEN psql \\
    "host=$HOST port=5432 dbname={_lb_db} user=$EMAIL sslmode=require" <<'SQL'
  CREATE SCHEMA IF NOT EXISTS {_lb_schema};
  GRANT USAGE, CREATE ON SCHEMA {_lb_schema} TO authenticator;
  ALTER DEFAULT PRIVILEGES IN SCHEMA {_lb_schema}
    GRANT ALL ON TABLES    TO authenticator;
  ALTER DEFAULT PRIVILEGES IN SCHEMA {_lb_schema}
    GRANT ALL ON SEQUENCES TO authenticator;
SQL
"""

import re as _re_mod

_schema_exists = False
try:
    _cur.execute(f"CREATE SCHEMA IF NOT EXISTS {_lb_schema}")
    _conn.commit()
    print(f"Schema '{_lb_schema}' created ✓")
    _schema_exists = True
except Exception as _schema_err:
    _conn.rollback()
    if "permission denied" in str(_schema_err).lower() or "insufficient" in str(_schema_err).lower():
        # Schema must be created by an admin from local terminal first
        try:
            _cur.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                (_lb_schema,)
            )
            _schema_exists = bool(_cur.fetchone())
        except Exception:
            _schema_exists = False

        if _schema_exists:
            print(f"Schema '{_lb_schema}' already exists — using it ✓")
        else:
            print(f"\n⚠️  Schema '{_lb_schema}' doesn't exist and 'authenticator' cannot create it.")
            print("    Run this ONCE from your local terminal, then re-run this cell:\n")
            print(_BOOTSTRAP_CMD)
            raise RuntimeError(
                f"Run the bootstrap commands above from your local terminal first."
            ) from None
    else:
        raise

# ── Apply DDL from Volume ──────────────────────────────────────────────────────
_sql_candidates = [
    f"{os.getenv('VOLUME_BASE', '')}/01_lakebase_schema.sql",
    "/Volumes/mircom_test/assistant_mochi/data/01_lakebase_schema.sql",
]
_schema_sql = None
for _sc in _sql_candidates:
    if _sc and _Path(_sc).exists():
        _schema_sql = _Path(_sc).read_text()
        print(f"Loaded DDL from {_sc}")
        break

if _schema_sql and _schema_exists:
    _stmts = [s.strip() for s in _re_mod.split(r";\s*\n", _schema_sql) if s.strip()]
    _ok = _fail = 0
    for _stmt in _stmts:
        try:
            _cur.execute(_stmt)
            _conn.commit()
            _ok += 1
        except Exception as _se:
            _conn.rollback()
            if "already exists" in str(_se).lower():
                _ok += 1
            else:
                print(f"  WARN: {str(_se)[:120]}")
                _fail += 1
    print(f"DDL applied: {_ok} ok, {_fail} warnings")
elif not _schema_sql:
    print("⚠️  DDL file not found — apply lakebase/sql/01_lakebase_schema.sql manually")

# ── Create a native Postgres role with a permanent password ───────────────────
# Per Databricks Lakebase docs, "password-based Postgres roles" are supported
# alongside OAuth roles. A native password NEVER expires — no token refresh needed.
import secrets as _secrets
import string as _string

_APP_ROLE = "assistant_app"
_alphabet  = _string.ascii_letters + _string.digits + "!@#$%^&*_-"
_native_pw = ''.join(_secrets.choice(_alphabet) for _ in range(40))

_cur.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{_APP_ROLE}') THEN
            CREATE ROLE {_APP_ROLE} LOGIN PASSWORD '{_native_pw}';
        ELSE
            ALTER ROLE {_APP_ROLE} PASSWORD '{_native_pw}';
        END IF;
    END $$;
""")
# Grant access to the schema and all objects
_cur.execute(f"GRANT USAGE ON SCHEMA {_lb_schema} TO {_APP_ROLE}")
_cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {_lb_schema} TO {_APP_ROLE}")
_cur.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {_lb_schema} TO {_APP_ROLE}")
_cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {_lb_schema} GRANT ALL ON TABLES TO {_APP_ROLE}")
_cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {_lb_schema} GRANT ALL ON SEQUENCES TO {_APP_ROLE}")
print(f"Native Postgres role '{_APP_ROLE}' created/updated ✓")

# ── Smoke test ────────────────────────────────────────────────────────────────
_cur.execute(f"SET search_path TO {_lb_schema}")
_cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = %s ORDER BY table_name
""", (_lb_schema,))
_tables = [r[0] for r in _cur.fetchall()]
_conn.close()

print(f"\n✓ Lakebase bootstrap complete")
print(f"  Tables in {_lb_schema}: {_tables if _tables else '(none yet — DDL not applied)'}")

# Persist OAuth token for this session
os.environ["LAKEBASE_PASSWORD"] = _lb_password
try:
    from virtual_assistant.agents.database import reset_config
    reset_config()
except ImportError:
    pass

print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⭐  PERMANENT CREDENTIALS — copy these into lakebase.env
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
print(f"LAKEBASE_USER={_APP_ROLE}")
print(f"LAKEBASE_PASSWORD={_native_pw}")
print("""
This native Postgres password NEVER expires.
After updating lakebase.env on the Volume, re-run cell 2a to reload env vars.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2c. Verify Lakebase Connection (after setup)
# MAGIC
# MAGIC Run this after the setup cell above has completed and `LAKEBASE_HOST` is set.

# COMMAND ----------
import uuid as _uuid, json as _json, requests as _req, psycopg2 as _pg2
import importlib.metadata as _imeta

# ── SDK version diagnostic ────────────────────────────────────────────────────
try:
    _sdk_ver = _imeta.version("databricks-sdk")
    print(f"databricks-sdk installed: {_sdk_ver}")
    _sdk_parts = tuple(int(x) for x in _sdk_ver.split(".")[:2])
    if _sdk_parts < (0, 61):
        print(f"  ⚠️  Version < 0.61 — w.database not available. Force-reinstall did not take effect.")
        print(f"     Try running the %pip install cell, then 'Clear State and Run All'.")
    else:
        print(f"  ✓ SDK version sufficient for w.database")
except Exception as _ve:
    print(f"  SDK version unknown: {_ve}")

# ── database.py version check ─────────────────────────────────────────────────
import sys as _sys
for _k in list(_sys.modules):
    if _k.startswith("virtual_assistant"):
        del _sys.modules[_k]
_REPO_PATH = "/Workspace/Users/mirco.meazzo@databricks.com/VirtualAssistant"
if _REPO_PATH not in _sys.path:
    _sys.path.insert(0, _REPO_PATH)
try:
    import virtual_assistant.agents.database as _dbm
    print(f"database.py  FILE_VERSION = {_dbm.FILE_VERSION}")
    if _dbm.FILE_VERSION != "v8-autoscaling-demo-2025":
        print("  ⚠️  Stale version — purge __pycache__ and retry")
    else:
        print("  ✓ Correct version")
except Exception as _ve2:
    print(f"  Cannot verify database.py version: {_ve2}")

# ── Config ────────────────────────────────────────────────────────────────────
_db_host   = os.getenv("DATABRICKS_HOST", "").strip().rstrip("/")
_db_token  = os.getenv("DATABRICKS_TOKEN", "").strip()
_lb_host   = os.getenv("LAKEBASE_HOST", "")
_lb_port   = int(os.getenv("LAKEBASE_PORT", "5432"))
_lb_db     = os.getenv("LAKEBASE_DB", "databricks_postgres")
_lb_user   = os.getenv("LAKEBASE_USER", "")
_lb_ssl    = os.getenv("LAKEBASE_SSLMODE", "require")
_lb_schema = os.getenv("LAKEBASE_SCHEMA", "assistant_mochi")
_instance  = os.getenv("LAKEBASE_INSTANCE_NAME", "assistant-demo").strip()

print(f"\nInstance : {_instance}")
print(f"LB host  : {_lb_host}")

# ── Generate OAuth token ──────────────────────────────────────────────────────
_lb_token = None
_auth_hdr = {"Authorization": f"Bearer {_db_token}", "Content-Type": "application/json"}
_body     = {"request_id": str(_uuid.uuid4()), "instance_names": [_instance]}

# Attempt 1: REST — try all known endpoint patterns
for _path in [
    "/api/2.0/database/generate-database-credential",
    "/api/2.1/database/generate-database-credential",
    f"/api/2.0/database/instances/{_instance}/generate-credential",
    f"/api/2.0/database/instances/{_instance}/credential",
    "/api/2.0/database/credential",
]:
    try:
        _r = _req.post(f"{_db_host}{_path}", headers=_auth_hdr, json=_body, timeout=30)
        if _r.status_code == 404:
            continue
        _r.raise_for_status()
        _d = _r.json()
        _lb_token = _d.get("token") or (_d.get("credential") or {}).get("token")
        if _lb_token:
            print(f"OAuth token via REST ({_path}): {len(_lb_token)} chars ✓")
            break
    except Exception:
        continue

# Attempt 2: Databricks SDK (w.database) — works if SDK >= 0.61 is active
if not _lb_token:
    try:
        from databricks.sdk import WorkspaceClient as _WC
        _w = _WC(host=_db_host, token=_db_token)
        _cred = _w.database.generate_database_credential(
            request_id=str(_uuid.uuid4()),
            instance_names=[_instance],
        )
        _lb_token = _cred.token
        print(f"OAuth token via SDK w.database: {len(_lb_token)} chars ✓")
    except AttributeError:
        print("SDK w.database not available — SDK version too old (force-reinstall needed)")
    except Exception as _sdk_err:
        print(f"SDK failed: {_sdk_err}")

# ── Connect ───────────────────────────────────────────────────────────────────
if _lb_token:
    try:
        _conn = _pg2.connect(
            host=_lb_host, port=_lb_port, dbname=_lb_db,
            user=_lb_user, password=_lb_token, sslmode=_lb_ssl,
            options=f"-c search_path={_lb_schema}",
        )
        _cur = _conn.cursor()
        _cur.execute("SELECT current_database(), current_schema(), version()")
        _row = _cur.fetchone()
        _conn.close()
        print(f"Connected  : db={_row[0]}  schema={_row[1]}")
        print(f"PG version : {_row[2][:60]}...")
        print("Lakebase connection OK ✓")
    except Exception as _conn_err:
        print(f"Connection failed: {_conn_err}")
else:
    print("\n⚠️  Could not generate OAuth token.")
    print("   All REST paths returned 404 and SDK w.database is unavailable.")
    print("   → Run '%pip install --force-reinstall \"databricks-sdk>=0.81.0\"' in a new cell")
    print("     then 'Clear State and Run All'.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Add Package to Python Path

# COMMAND ----------
# Path where the code is synced in Databricks Workspace
REPO_PATH = "/Workspace/Users/mirco.meazzo@databricks.com/VirtualAssistant"

if REPO_PATH not in sys.path:
    sys.path.insert(0, REPO_PATH)
    print(f"Added to sys.path: {REPO_PATH}")

# Verify import
try:
    from virtual_assistant.core.business_config import BusinessConfig
    from virtual_assistant.core.engine_impl import DatabricksConversationEngine
    from virtual_assistant.integrations.databricks import create_databricks_predict_fn
    print("virtual_assistant package imported successfully")
except ImportError as e:
    raise ImportError(
        f"Cannot import virtual_assistant: {e}\n"
        f"Make sure the code is synced to {REPO_PATH} and the path is correct."
    )

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Initialize Engine

# COMMAND ----------
# Two predict functions for minimum latency on real-time phone calls:
#   router_predict_fn  — temperature=0  → deterministic JSON extraction, tight token budget
#   response_predict_fn — temperature=0.3 → natural conversational replies
router_predict_fn   = create_databricks_predict_fn(temperature=0.0)
response_predict_fn = create_databricks_predict_fn(temperature=0.3)

# Smoke test the LLM endpoint
try:
    test_resp = response_predict_fn("Reply with exactly one word: hello", max_tokens=10)
    print(f"LLM endpoint OK: '{test_resp.strip()}'")
except Exception as e:
    print(f"WARNING: LLM endpoint test failed: {e}")

# Build the engine (no DB connection yet — lazy init)
engine = DatabricksConversationEngine(
    predict_fn=response_predict_fn,
    router_predict_fn=router_predict_fn,
)
print("Engine initialized")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Create Session
# MAGIC
# MAGIC This step calls the LLM to generate a **custom system prompt** for your business.

# COMMAND ----------
import asyncio

session_result = asyncio.run(engine.create_session(
    business_config={
        "name"                : business_name,
        "business_type"       : business_type,
        "services"            : services,
        "language"            : language,
        "tone"                : tone,
        "special_instructions": special_instr,
        "agent_capabilities"  : ["check_availability", "book_appointment"],
    },
    customer_context={},
))

SESSION_ID = session_result["session_id"]

print(f"\nSession created: {SESSION_ID}")
print(f"\n--- Generated System Prompt ---")
print(session_result["generated_system_prompt"])
print(f"\n--- Opening Greeting ---")
print(session_result["greeting"])

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. Test Conversation (Text)

# COMMAND ----------
def chat(text: str, customer_id: str = "CUST001") -> str:
    """Send a turn and print the result."""
    result = asyncio.run(engine.process_turn(
        session_id=SESSION_ID,
        text=text,
        audio_base64=None,
        customer_id=customer_id,
    ))
    if result is None:
        return "(session not found)"

    print(f"\n{'─'*60}")
    print(f"You      : {text}")
    if result.get("filler_text"):
        print(f"[filler] : {result['filler_text']}")
    print(f"Assistant: {result['response_text']}")
    print(f"Action   : {result.get('action')} | {result['processing_time_ms']:.0f}ms | phase={result['phase']}")
    return result["response_text"]

# --- Run test messages based on business type ---
if business_type == "hair_salon":
    test_messages = [
        "Ciao, vorrei prenotare un taglio per domani mattina" if language == "it"
        else "Hi, I'd like to book a haircut for tomorrow morning",
        "Verso le 10, se possibile" if language == "it"
        else "Around 10am if possible",
    ]
elif business_type == "restaurant":
    test_messages = [
        "Buonasera, vorrei prenotare un tavolo per sabato sera" if language == "it"
        else "Good evening, I'd like to book a table for Saturday evening",
        "Siamo in quattro" if language == "it"
        else "There will be four of us",
    ]
elif business_type == "dental_clinic":
    test_messages = [
        "Salve, ho bisogno di un appuntamento per una visita di controllo" if language == "it"
        else "Hello, I need an appointment for a check-up",
    ]
else:
    test_messages = [
        "Ciao, come funziona?" if language == "it" else "Hello, how does this work?",
        "Vorrei prenotare un servizio" if language == "it" else "I'd like to book a service",
    ]

print(f"Opening: {session_result['greeting']}")
for msg in test_messages:
    chat(msg)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. Interactive Cell
# MAGIC
# MAGIC 1. Type your message in the **💬 Your message** widget at the top of the notebook
# MAGIC 2. Press **Shift + Enter** (or click ▶ Run Cell) on **this cell** to send it
# MAGIC 3. Repeat for each turn

# COMMAND ----------
# Read the widget value — do NOT call dbutils.widgets.text() here, that would reset it to ""
user_message = dbutils.widgets.get("USER_MESSAGE").strip()

if not user_message:
    print("👆 Type your message in the 'Your message' widget above, then re-run this cell (Shift+Enter).")
else:
    # Guard: check session is alive before sending
    _session = engine._sessions.get(SESSION_ID)
    if _session is None:
        print(f"⚠️  Session '{SESSION_ID[:8]}...' not found in engine.")
        print("   The engine may have been re-initialised without recreating the session.")
        print("   → Re-run cell 5 ('Create Session') to start a new session, then come back here.")
    else:
        # Send the turn
        result = asyncio.run(engine.process_turn(
            session_id=SESSION_ID,
            text=user_message,
            audio_base64=None,
            customer_id="CUST001",
        ))

        if result is None:
            print("⚠️  process_turn returned None — session may have expired.")
        else:
            if result.get("filler_text"):
                print(f"[filler] : {result['filler_text']}")
            print(f"Assistant: {result['response_text']}")
            print(f"Action   : {result.get('action')} | {result['processing_time_ms']:.0f}ms")

        # Show full conversation history
        print("\n─── Full conversation ───")
        for turn in _session.history:
            role = "You      " if turn.role == "user" else "Assistant"
            print(f"  {role}: {turn.content}")

        # Clear the widget so next run doesn't re-send the same message
        dbutils.widgets.text("USER_MESSAGE", "", "💬 Your message (re-run this cell to send)")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 8. Voice Input (Optional)
# MAGIC
# MAGIC Provide a WAV file path in a Volume to test speech-to-text.

# COMMAND ----------
dbutils.widgets.text("AUDIO_PATH", "", "Audio file path (WAV in Volume)")
audio_path = dbutils.widgets.get("AUDIO_PATH").strip()

if audio_path and Path(audio_path).exists():
    import base64
    audio_b64 = base64.b64encode(Path(audio_path).read_bytes()).decode()

    result = asyncio.run(engine.process_turn(
        session_id=SESSION_ID,
        text=None,
        audio_base64=audio_b64,
        customer_id="CUST001",
    ))
    print(f"Transcribed : {result['user_text']}")
    print(f"Assistant   : {result['response_text']}")
    if result.get("audio_base64") and enable_tts:
        out_path = f"{volume_base}/audio/response.wav"
        Path(out_path).write_bytes(base64.b64decode(result["audio_base64"]))
        print(f"Audio saved : {out_path}")
else:
    print("No audio file configured. Set AUDIO_PATH to a WAV file in a Volume to test voice.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 9. Session Summary & End

# COMMAND ----------
summary = asyncio.run(engine.get_session_summary(SESSION_ID))
print("Session Summary:")
for k, v in summary.items():
    print(f"  {k}: {v}")

# COMMAND ----------
end_result = asyncio.run(engine.end_session(SESSION_ID))
print(f"\nFarewell: {end_result['farewell']}")
print(f"Total turns: {end_result['summary']['turn_count']}")
print(f"Duration: {end_result['summary']['duration_seconds']:.1f}s")
