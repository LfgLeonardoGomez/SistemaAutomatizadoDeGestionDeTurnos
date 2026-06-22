import os
import pytest
from pydantic import ValidationError


class TestSettings:
    """Tests for Pydantic Settings configuration management."""

    def test_settings_loads_with_all_required_vars(self, monkeypatch):
        """Scenario: Startup with all required variables."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", "{}")
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")
        monkeypatch.setenv("N8N_WEBHOOK_URL", "https://n8n.example.com/webhook")
        monkeypatch.setenv("RESERVA_TEMPORAL_MINUTOS", "10")
        monkeypatch.setenv("RECORDATORIO_HORAS_ANTES", "24")
        monkeypatch.setenv("ENV", "development")

        from app.config import Settings
        settings = Settings()
        assert settings.database_url == "postgresql+asyncpg://user:pass@localhost/db"
        assert settings.env == "development"

    def test_settings_fails_without_database_url(self, monkeypatch):
        """Scenario: Startup with missing required variable."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", "{}")
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")
        monkeypatch.setenv("N8N_WEBHOOK_URL", "https://n8n.example.com/webhook")
        monkeypatch.setenv("RESERVA_TEMPORAL_MINUTOS", "10")
        monkeypatch.setenv("RECORDATORIO_HORAS_ANTES", "24")
        monkeypatch.setenv("ENV", "development")

        from app.config import Settings
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "database_url" in str(exc_info.value)

    def test_settings_optional_defaults(self, monkeypatch):
        """Scenario: Startup with optional variables using defaults."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", "{}")
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")
        monkeypatch.setenv("N8N_WEBHOOK_URL", "https://n8n.example.com/webhook")
        monkeypatch.delenv("RESERVA_TEMPORAL_MINUTOS", raising=False)
        monkeypatch.delenv("RECORDATORIO_HORAS_ANTES", raising=False)
        monkeypatch.delenv("RECORDATORIO_JOB_INTERVAL_MINUTOS", raising=False)
        monkeypatch.setenv("ENV", "development")

        from app.config import Settings
        settings = Settings()
        assert settings.reserva_temporal_minutos == 10
        assert settings.recordatorio_horas_antes == 24
        assert settings.recordatorio_job_interval_minutos == 60

    def test_settings_calendar_retry_vars(self, monkeypatch):
        """Scenario: Calendar retry variables are loaded correctly."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", "{}")
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "my_calendar")
        monkeypatch.setenv("GOOGLE_CALENDAR_MAX_RETRIES", "5")
        monkeypatch.setenv("GOOGLE_CALENDAR_BASE_DELAY", "2.0")
        monkeypatch.setenv("GOOGLE_CALENDAR_MAX_DELAY", "20.0")
        monkeypatch.setenv("N8N_WEBHOOK_URL", "")
        monkeypatch.setenv("ENV", "test")

        from app.config import Settings
        settings = Settings()
        assert settings.google_calendar_id == "my_calendar"
        assert settings.google_calendar_max_retries == 5
        assert settings.google_calendar_base_delay == 2.0
        assert settings.google_calendar_max_delay == 20.0

    def test_settings_recordatorio_job_interval_custom(self, monkeypatch):
        """Scenario: RECORDATORIO_JOB_INTERVAL_MINUTOS custom value."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", "{}")
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")
        monkeypatch.setenv("RECORDATORIO_JOB_INTERVAL_MINUTOS", "30")
        monkeypatch.setenv("N8N_WEBHOOK_URL", "")
        monkeypatch.setenv("ENV", "test")

        from app.config import Settings
        settings = Settings()
        assert settings.recordatorio_job_interval_minutos == 30
