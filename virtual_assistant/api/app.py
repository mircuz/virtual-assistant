"""
FastAPI application for the Virtual Assistant API.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from virtual_assistant.api.routes import health, sessions
from virtual_assistant.core.engine import ConversationEngine, init_engine


def _create_engine_from_env() -> ConversationEngine:
    """
    Create ConversationEngine from environment variables.

    Required env vars:
    - DATABRICKS_HOST: Databricks workspace URL
    - DATABRICKS_TOKEN: API token (or available via notebook context)
    - DATABRICKS_ENDPOINT: Model serving endpoint name (default: personaplex-7b-endpoint)
    """
    from virtual_assistant.integrations.databricks import create_databricks_predict_fn
    from virtual_assistant.core.engine_impl import DatabricksConversationEngine

    predict_fn = create_databricks_predict_fn()
    return DatabricksConversationEngine(predict_fn)


app = FastAPI(
    title="Virtual Assistant API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sessions.router)


@app.on_event("startup")
async def startup() -> None:
    """Initialize the conversation engine from environment variables."""
    engine = _create_engine_from_env()
    init_engine(engine)
