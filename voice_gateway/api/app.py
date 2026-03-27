"""Voice Gateway FastAPI application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire up booking client and OpenAI Realtime API key."""
    try:
        from voice_gateway.config import Settings
        settings = Settings()
        print(f"[VG] Settings loaded: booking_url={settings.booking_engine_url}")

        # Auto-detect Databricks host and token from SDK
        if not settings.databricks_token:
            try:
                from databricks.sdk import WorkspaceClient
                w = WorkspaceClient()
                settings.databricks_host = settings.databricks_host or w.config.host
                me = w.current_user.me()
                print(f"[VG] SDK identity: {me.user_name}")
                auth = w.config.authenticate()
                if callable(auth):
                    header = {}
                    auth(header)
                    token = header.get("Authorization", "").replace("Bearer ", "")
                elif isinstance(auth, dict):
                    token = auth.get("Authorization", "").replace("Bearer ", "")
                else:
                    token = ""
                    print(f"[VG] Unknown auth type: {type(auth)} = {str(auth)[:100]}")
                if not token:
                    try:
                        api_client = w.api_client
                        token = getattr(api_client, '_token', '') or ''
                        if not token and hasattr(api_client, '_header_factory'):
                            hdr = api_client._header_factory()
                            token = hdr.get("Authorization", "").replace("Bearer ", "")
                    except Exception as e2:
                        print(f"[VG] Token extraction fallback failed: {e2}")
                settings.databricks_token = token
                print(f"[VG] SDK auth: host={settings.databricks_host} token_len={len(settings.databricks_token)}")
            except Exception as e:
                import traceback
                print(f"[VG] SDK auth failed: {e}\n{traceback.format_exc()}")

        from voice_gateway.clients.booking_client import BookingClient
        bc = BookingClient(base_url=settings.booking_engine_url, auth_token=settings.databricks_token)
        await bc.__aenter__()
        app.state.booking_client = bc
        print(f"[VG] Booking client connected: {settings.booking_engine_url}")

        # OpenAI Realtime API key
        app.state._openai_key = settings.openai_key
        print(f"[VG] Realtime API: {'enabled' if settings.openai_key else 'disabled'}")
    except Exception as e:
        import traceback
        print(f"[VG] Lifespan init FAILED: {e}\n{traceback.format_exc()}")

    yield

    if hasattr(app.state, 'booking_client') and app.state.booking_client:
        await app.state.booking_client.__aexit__(None, None, None)


def create_app() -> FastAPI:
    import pathlib
    app = FastAPI(title="Virtual Assistant Voice Gateway", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )

    from voice_gateway.api.routes import realtime
    app.include_router(realtime.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    # Serve test UI
    static_dir = pathlib.Path(__file__).resolve().parent.parent / "static"
    if static_dir.exists():
        from fastapi.responses import FileResponse
        @app.get("/")
        async def ui():
            return FileResponse(static_dir / "index.html")

    return app
