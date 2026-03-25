"""Booking Engine FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from booking_engine.config import Settings
from booking_engine.db.connection import init_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    pool = await init_pool(settings)
    app.state.pool = pool
    yield
    await close_pool()


def create_app() -> FastAPI:
    app = FastAPI(title="Hair Salon Booking Engine", version="1.0.0")
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


def get_pool(request: Request):
    return request.app.state.pool
