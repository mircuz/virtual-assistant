"""Fixtures for voice gateway route tests."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from voice_gateway.api.routes import realtime


@pytest.fixture
def mock_booking() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def app(mock_booking) -> FastAPI:
    app = FastAPI()
    app.state.booking_client = mock_booking
    app.state._openai_key = "test-openai-key"
    app.include_router(realtime.router)
    return app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
