"""Tests for the AWS Lambda Mangum handler."""
from __future__ import annotations

from unittest.mock import patch, AsyncMock


class TestLambdaHandler:
    def test_handler_is_callable(self):
        with (
            patch("booking_engine.api.app.Settings"),
            patch("booking_engine.api.app.init_connection", new_callable=AsyncMock),
            patch("booking_engine.api.app.close_connection", new_callable=AsyncMock),
        ):
            from lambda_handler import handler
            assert callable(handler)

    def test_health_endpoint_via_lambda(self):
        with (
            patch("booking_engine.api.app.Settings"),
            patch("booking_engine.api.app.init_connection", new_callable=AsyncMock),
            patch("booking_engine.api.app.close_connection", new_callable=AsyncMock),
        ):
            from lambda_handler import handler

            event = {
                "version": "2.0",
                "requestContext": {
                    "http": {
                        "method": "GET",
                        "path": "/health",
                        "sourceIp": "127.0.0.1",
                    },
                    "accountId": "123456789012",
                    "apiId": "test",
                    "stage": "$default",
                },
                "rawPath": "/health",
                "rawQueryString": "",
                "headers": {},
                "isBase64Encoded": False,
            }

            response = handler(event, {})
            assert response["statusCode"] == 200
