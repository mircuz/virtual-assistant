"""Voice Gateway FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from voice_gateway.conversation.session import SessionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire up real clients from env vars if available."""
    try:
        from voice_gateway.config import Settings
        settings = Settings()
        from voice_gateway.clients.booking_client import BookingClient
        bc = BookingClient(base_url=settings.booking_engine_url)
        await bc.__aenter__()
        app.state.booking_client = bc

        from voice_gateway.voice.stt import STTClient
        from voice_gateway.voice.tts import TTSClient
        app.state.stt = STTClient(settings.databricks_host, settings.databricks_token, settings.stt_endpoint)
        app.state.tts = TTSClient(settings.databricks_host, settings.databricks_token, settings.tts_endpoint)

        from voice_gateway.llm import make_predict_fn
        app.state.intent_predict = make_predict_fn(settings.databricks_host, settings.databricks_token, settings.intent_llm_endpoint)
        app.state.response_predict = make_predict_fn(settings.databricks_host, settings.databricks_token, settings.response_llm_endpoint)
    except Exception:
        # Allow app to start without env vars (for testing)
        pass

    yield

    if hasattr(app.state, 'booking_client') and app.state.booking_client:
        await app.state.booking_client.__aexit__(None, None, None)


def create_app() -> FastAPI:
    app = FastAPI(title="Hair Salon Voice Gateway", version="1.0.0")
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
