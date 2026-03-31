"""Tests for GET /api/v1/shops/{shop_id}."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.conftest import SHOP_ID


class TestReadShop:
    def test_returns_shop(self, client, fake_shop):
        with patch("booking_engine.api.routes.shops.get_shop", new_callable=AsyncMock, return_value=fake_shop):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Salone Bella"

    def test_returns_404_when_not_found(self, client):
        with patch("booking_engine.api.routes.shops.get_shop", new_callable=AsyncMock, return_value=None):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}")
        assert resp.status_code == 404
        assert resp.json()["error"] == "shop_not_found"

    def test_invalid_uuid_returns_422(self, client):
        resp = client.get("/api/v1/shops/not-a-uuid")
        assert resp.status_code == 422
