"""Voice Gateway FastAPI application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from voice_gateway.conversation.session import SessionManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire up real clients from env vars if available."""
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
                # Force token generation by making an API call
                me = w.current_user.me()
                print(f"[VG] SDK identity: {me.user_name}")
                # Extract the token - authenticate() returns either a callable or a dict
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
                    # Try the internal API client headers
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

        app.state.stt = None
        app.state.tts = None
        if settings.stt_endpoint:
            from voice_gateway.voice.stt import STTClient
            app.state.stt = STTClient(settings.databricks_host, settings.databricks_token, settings.stt_endpoint)
        if settings.tts_url:
            from voice_gateway.voice.tts import TTSClient
            app.state.tts = TTSClient(settings.tts_url, settings.databricks_token)
        print(f"[VG] STT={'enabled' if app.state.stt else 'disabled'} TTS={'enabled' if app.state.tts else 'disabled'}")

        from voice_gateway.llm import make_predict_fn
        app.state.intent_predict = make_predict_fn(settings.databricks_host, settings.databricks_token, settings.intent_llm_endpoint)
        app.state.response_predict = make_predict_fn(settings.databricks_host, settings.databricks_token, settings.response_llm_endpoint)
        print(f"[VG] LLM endpoints: intent={settings.intent_llm_endpoint} response={settings.response_llm_endpoint}")
    except Exception as e:
        import traceback
        print(f"[VG] Lifespan init FAILED: {e}\n{traceback.format_exc()}")

    yield

    if hasattr(app.state, 'booking_client') and app.state.booking_client:
        await app.state.booking_client.__aexit__(None, None, None)


def create_app() -> FastAPI:
    app = FastAPI(title="Virtual Assistant Voice Gateway", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )
    app.state.session_manager = SessionManager()

    from voice_gateway.api.routes import conversations, ws
    app.include_router(conversations.router)
    app.include_router(ws.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
