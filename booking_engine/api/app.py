"""Booking Engine FastAPI application."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from booking_engine.config import Settings
from booking_engine.db.connection import init_connection, close_connection

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()

    # Auto-detect token from Databricks SDK if not set
    if not settings.databricks_token:
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient()
            settings.databricks_server_hostname = settings.databricks_server_hostname or w.config.host.replace("https://", "")
            auth = w.config.authenticate()
            if callable(auth):
                header = {}
                auth(header)
                settings.databricks_token = header.get("Authorization", "").replace("Bearer ", "")
            elif isinstance(auth, dict):
                settings.databricks_token = auth.get("Authorization", "").replace("Bearer ", "")
            # Auto-detect HTTP path from serverless or default warehouse
            if not settings.databricks_http_path:
                whs = list(w.warehouses.list())
                for wh in whs:
                    if wh.state and wh.state.value == "RUNNING":
                        settings.databricks_http_path = f"/sql/1.0/warehouses/{wh.id}"
                        break
                if not settings.databricks_http_path and whs:
                    settings.databricks_http_path = f"/sql/1.0/warehouses/{whs[0].id}"
            logger.info("SDK auth: host=%s http_path=%s", settings.databricks_server_hostname, settings.databricks_http_path)
        except Exception as e:
            logger.error("SDK auth failed: %s", e)

    logger.info("Connecting to Databricks SQL at %s catalog=%s schema=%s",
                settings.databricks_server_hostname, settings.databricks_catalog, settings.databricks_schema)
    await init_connection(settings)
    logger.info("Databricks SQL connection initialized")
    yield
    await close_connection()


def create_app() -> FastAPI:
    app = FastAPI(title="Virtual Assistant Booking Engine", version="1.0.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    from booking_engine.api.routes import shops, customers, services, availability, appointments
    app.include_router(shops.router, prefix="/api/v1")
    app.include_router(customers.router, prefix="/api/v1")
    app.include_router(services.router, prefix="/api/v1")
    app.include_router(availability.router, prefix="/api/v1")
    app.include_router(appointments.router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        return {"status": "ok"}
    return app
