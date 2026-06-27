import pytest
from unittest.mock import patch

from tests.conftest import make_profesional


class TestWebhooksRouter:
    @pytest.mark.asyncio
    async def test_post_webhook_telegram_valid(self, api_client, db_session, profesional):
        """Scenario: POST /webhooks/telegram con secret token válido → 200."""
        profesional.telegram_secret_token = "valid-secret-token"
        profesional.telegram_bot_token = "test-bot-token"
        await db_session.commit()

        payload = {
            "update_id": 123,
            "message": {
                "message_id": 1,
                "date": 1,
                "chat": {"id": 1, "type": "private"},
                "text": "/start",
            },
        }

        with patch("app.routers.webhooks.procesar_update_async") as mock_process:
            response = api_client.post(
                "/webhooks/telegram",
                json=payload,
                headers={"X-Telegram-Bot-Api-Secret-Token": "valid-secret-token"},
            )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_process.assert_called_once()
        args, kwargs = mock_process.call_args
        assert kwargs["profesional_id"] == profesional.id

    @pytest.mark.asyncio
    async def test_post_webhook_telegram_secret_invalid(self, api_client, db_session, profesional):
        """Scenario: POST /webhooks/telegram con secret token inválido → 403."""
        payload = {
            "update_id": 123,
            "message": {
                "message_id": 1,
                "date": 1,
                "chat": {"id": 1, "type": "private"},
                "text": "/start",
            },
        }
        response = api_client.post(
            "/webhooks/telegram",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "invalid-token"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_post_webhook_telegram_no_secret(self, api_client, db_session, profesional):
        """Scenario: POST /webhooks/telegram sin secret token → 403."""
        payload = {
            "update_id": 123,
            "message": {
                "message_id": 1,
                "date": 1,
                "chat": {"id": 1, "type": "private"},
                "text": "/start",
            },
        }
        response = api_client.post("/webhooks/telegram", json=payload)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_post_webhook_telegram_malformed_payload(self, api_client, db_session, profesional):
        """Scenario: POST /webhooks/telegram con payload inválido → 400."""
        profesional.telegram_secret_token = "valid-secret-token"
        await db_session.commit()

        payload = {"invalid": "payload"}
        response = api_client.post(
            "/webhooks/telegram",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "valid-secret-token"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_post_webhook_telegram_multiple_profesionales(self, api_client, db_session, profesional):
        """Scenario: POST /webhooks/telegram con distintos secret tokens rutea correctamente."""
        profesional.telegram_secret_token = "secret-a"
        profesional.telegram_bot_token = "bot-a"
        await db_session.commit()

        otro = make_profesional(
            nombre="Dr. B",
            dias_atencion=["Lunes"],
            email="drb@local.dev",
            password_hash="fakehash",
            telegram_secret_token="secret-b",
            telegram_bot_token="bot-b",
        )
        db_session.add(otro)
        await db_session.commit()
        await db_session.refresh(otro)

        payload = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "date": 1,
                "chat": {"id": 1, "type": "private"},
                "text": "/start",
            },
        }

        with patch("app.routers.webhooks.procesar_update_async") as mock_process:
            response = api_client.post(
                "/webhooks/telegram",
                json=payload,
                headers={"X-Telegram-Bot-Api-Secret-Token": "secret-b"},
            )
        assert response.status_code == 200
        args, kwargs = mock_process.call_args
        assert kwargs["profesional_id"] == otro.id
