import pytest
from fastapi import status
from unittest.mock import patch


class TestTelegramWebhook:
    """Tests for POST /webhooks/telegram endpoint."""

    def test_webhook_valid_secret_token(self, api_client, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "supersecret")
        payload = {
            "update_id": 1,
            "message": {"message_id": 1, "chat": {"id": 123}, "text": "/start"},
        }
        with patch("app.routers.webhooks.procesar_update_async"):
            response = api_client.post(
                "/webhooks/telegram",
                json=payload,
                headers={"X-Telegram-Bot-Api-Secret-Token": "supersecret"},
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ok"

    def test_webhook_invalid_secret_token(self, api_client, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "supersecret")
        payload = {"update_id": 1, "message": {"chat": {"id": 123}, "text": "/start"}}
        response = api_client.post(
            "/webhooks/telegram",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "badsecret"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_webhook_missing_secret_token_when_configured(self, api_client, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "supersecret")
        payload = {"update_id": 1, "message": {"chat": {"id": 123}, "text": "/start"}}
        response = api_client.post("/webhooks/telegram", json=payload)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_webhook_no_secret_token_when_not_configured(self, api_client, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "")
        payload = {
            "update_id": 1,
            "message": {"message_id": 1, "chat": {"id": 123}, "text": "/start"},
        }
        with patch("app.routers.webhooks.procesar_update_async"):
            response = api_client.post("/webhooks/telegram", json=payload)
        assert response.status_code == status.HTTP_200_OK

    def test_webhook_malformed_payload(self, api_client):
        """Missing update_id should be considered malformed."""
        payload = {"message": "not a dict"}
        response = api_client.post("/webhooks/telegram", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_webhook_callback_query_payload(self, api_client):
        """Callback query payload should be accepted as valid."""
        payload = {
            "update_id": 2,
            "callback_query": {
                "id": "cq1",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 1, "chat": {"id": 123}, "text": "msg"},
                "data": "fecha:2026-06-15",
            },
        }
        with patch("app.routers.webhooks.procesar_update_async"):
            response = api_client.post("/webhooks/telegram", json=payload)
        assert response.status_code == status.HTTP_200_OK

    def test_webhook_malformed_update_id_type(self, api_client):
        """update_id as string should be considered malformed."""
        payload = {"update_id": "not-an-int", "message": {"chat": {"id": 123}}}
        response = api_client.post("/webhooks/telegram", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
