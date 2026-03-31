"""Tests for services and staff routes."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.conftest import SHOP_ID, STAFF_ID_1


class TestReadServices:
    def test_returns_services(self, client, fake_services_list):
        with patch("booking_engine.api.routes.services.list_services",
                    new_callable=AsyncMock, return_value=fake_services_list):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/services")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_returns_empty_list(self, client):
        with patch("booking_engine.api.routes.services.list_services",
                    new_callable=AsyncMock, return_value=[]):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/services")
        assert resp.status_code == 200
        assert resp.json() == []


class TestReadStaff:
    def test_returns_staff(self, client, fake_staff_list):
        with patch("booking_engine.api.routes.services.list_staff",
                    new_callable=AsyncMock, return_value=fake_staff_list):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/staff")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestReadStaffServices:
    def test_returns_staff_services(self, client, fake_services_list):
        with patch("booking_engine.api.routes.services.get_staff_services",
                    new_callable=AsyncMock, return_value=fake_services_list):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/staff/{STAFF_ID_1}/services")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
