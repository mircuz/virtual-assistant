"""Tests for customer lookup and creation routes."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.conftest import SHOP_ID


class TestLookupCustomers:
    def test_search_by_phone(self, client, fake_customer):
        with patch("booking_engine.api.routes.customers.find_customers_by_phone",
                    new_callable=AsyncMock, return_value=[fake_customer]):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/customers", params={"phone": "+39123"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_by_name_and_phone(self, client, fake_customer):
        with patch("booking_engine.api.routes.customers.find_customers_by_name_and_phone",
                    new_callable=AsyncMock, return_value=[fake_customer]):
            resp = client.get(f"/api/v1/shops/{SHOP_ID}/customers",
                              params={"phone": "+39123", "name": "Anna"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_no_params_returns_empty(self, client):
        resp = client.get(f"/api/v1/shops/{SHOP_ID}/customers")
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateCustomer:
    def test_creates_customer(self, client, fake_customer):
        with patch("booking_engine.api.routes.customers.create_customer",
                    new_callable=AsyncMock, return_value=fake_customer):
            resp = client.post(
                f"/api/v1/shops/{SHOP_ID}/customers",
                json={"full_name": "Anna Verdi", "phone_number": "+39123"},
            )
        assert resp.status_code == 201
        assert resp.json()["full_name"] == "Anna Verdi"

    def test_missing_name_returns_422(self, client):
        resp = client.post(f"/api/v1/shops/{SHOP_ID}/customers", json={})
        assert resp.status_code == 422
