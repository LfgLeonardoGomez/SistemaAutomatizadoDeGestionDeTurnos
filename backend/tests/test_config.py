import os
import pytest
from pydantic import ValidationError


class TestSettings:
    """Tests for Pydantic Settings configuration management."""

    def test_settings_loads_with_all_required_vars(self, monkeypatch):
        """Scenario: Startup with all required variables."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("N8N_WEBHOOK_URL", "https://n8n.example.com/webhook")
        monkeypatch.setenv("RESERVA_TEMPORAL_MINUTOS", "10")
        monkeypatch.setenv("RECORDATORIO_HORAS_ANTES", "24")
        monkeypatch.setenv("ENV", "development")
        monkeypatch.setenv("SECRET_KEY", "testsecret")

        from app.config import Settings
        settings = Settings()
        assert settings.database_url == "postgresql+asyncpg://user:pass@localhost/db"
        assert settings.env == "development"
        assert not hasattr(settings, "telegram_bot_token")
        assert not hasattr(settings, "google_calendar_credentials")
        assert not hasattr(settings, "google_calendar_id")

    def test_settings_fails_without_database_url(self, monkeypatch):
        """Scenario: Startup with missing required variable."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("N8N_WEBHOOK_URL", "https://n8n.example.com/webhook")
        monkeypatch.setenv("RESERVA_TEMPORAL_MINUTOS", "10")
        monkeypatch.setenv("RECORDATORIO_HORAS_ANTES", "24")
        monkeypatch.setenv("ENV", "development")
        monkeypatch.setenv("SECRET_KEY", "testsecret")

        from app.config import Settings
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "database_url" in str(exc_info.value)

    def test_settings_optional_defaults(self, monkeypatch):
        """Scenario: Startup with optional variables using defaults."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("N8N_WEBHOOK_URL", "https://n8n.example.com/webhook")
        monkeypatch.delenv("RESERVA_TEMPORAL_MINUTOS", raising=False)
        monkeypatch.delenv("RECORDATORIO_HORAS_ANTES", raising=False)
        monkeypatch.delenv("RECORDATORIO_JOB_INTERVAL_MINUTOS", raising=False)
        monkeypatch.setenv("ENV", "development")
        monkeypatch.setenv("SECRET_KEY", "testsecret")

        from app.config import Settings
        settings = Settings()
        assert settings.reserva_temporal_minutos == 10
        assert settings.recordatorio_horas_antes == 24
        assert settings.recordatorio_job_interval_minutos == 60

    def test_settings_calendar_retry_vars(self, monkeypatch):
        """Scenario: Calendar retry variables are loaded correctly."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("GOOGLE_CALENDAR_MAX_RETRIES", "5")
        monkeypatch.setenv("GOOGLE_CALENDAR_BASE_DELAY", "2.0")
        monkeypatch.setenv("GOOGLE_CALENDAR_MAX_DELAY", "20.0")
        monkeypatch.setenv("N8N_WEBHOOK_URL", "")
        monkeypatch.setenv("ENV", "test")
        monkeypatch.setenv("SECRET_KEY", "testsecret")

        from app.config import Settings
        settings = Settings()
        assert settings.google_calendar_max_retries == 5
        assert settings.google_calendar_base_delay == 2.0
        assert settings.google_calendar_max_delay == 20.0

    def test_settings_recordatorio_job_interval_custom(self, monkeypatch):
        """Scenario: RECORDATORIO_JOB_INTERVAL_MINUTOS custom value."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("RECORDATORIO_JOB_INTERVAL_MINUTOS", "30")
        monkeypatch.setenv("N8N_WEBHOOK_URL", "")
        monkeypatch.setenv("ENV", "test")
        monkeypatch.setenv("SECRET_KEY", "testsecret")

        from app.config import Settings
        settings = Settings()
        assert settings.recordatorio_job_interval_minutos == 30

    def test_settings_secret_key_and_algorithm(self, monkeypatch):
        """Scenario: SECRET_KEY y ALGORITHM disponibles."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "supersecretkey")
        monkeypatch.setenv("ALGORITHM", "HS512")
        monkeypatch.setenv("N8N_WEBHOOK_URL", "")
        monkeypatch.setenv("ENV", "test")

        from app.config import Settings
        settings = Settings()
        assert settings.secret_key == "supersecretkey"
        assert settings.algorithm == "HS512"

    def test_settings_algorithm_default(self, monkeypatch):
        """Scenario: ALGORITHM default es HS256."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "supersecretkey")
        monkeypatch.delenv("ALGORITHM", raising=False)
        monkeypatch.setenv("N8N_WEBHOOK_URL", "")
        monkeypatch.setenv("ENV", "test")

        from app.config import Settings
        settings = Settings()
        assert settings.algorithm == "HS256"

    def test_settings_does_not_expose_n8n_webhook_url(self, monkeypatch):
        """Spec: N8N_WEBHOOK_URL is not declared in Pydantic Settings.

        Scenario: n8n_webhook_url is dead config — it MUST NOT be exposed.
        """
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "testsecret")
        monkeypatch.setenv("ENV", "test")
        monkeypatch.delenv("N8N_WEBHOOK_URL", raising=False)

        from app.config import Settings
        settings = Settings()
        assert not hasattr(settings, "n8n_webhook_url"), (
            "n8n_webhook_url is dead config and must be removed from Settings"
        )

    def test_settings_does_not_expose_telegram_webhook_secret(self, monkeypatch):
        """Spec: TELEGRAM_WEBHOOK_SECRET is not declared in Pydantic Settings.

        Scenario: telegram_webhook_secret was replaced by per-professional tokens
        in C-16 and MUST NOT be exposed anymore.
        """
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "testsecret")
        monkeypatch.setenv("ENV", "test")
        monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)

        from app.config import Settings
        settings = Settings()
        assert not hasattr(settings, "telegram_webhook_secret"), (
            "telegram_webhook_secret was replaced by per-professional tokens; "
            "it must be removed from Settings"
        )

    def test_settings_exposes_super_admin_password_not_hash(self, monkeypatch):
        """Spec: Super-admin bootstrap uses plain-text SUPER_ADMIN_PASSWORD.

        Scenario: the field is renamed from super_admin_password_hash to
        super_admin_password and accepts a plain-text value.
        """
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "testsecret")
        monkeypatch.setenv("ENV", "test")
        monkeypatch.setenv("SUPER_ADMIN_PASSWORD", "plaintext-secret-123")

        from app.config import Settings
        settings = Settings()
        assert hasattr(settings, "super_admin_password"), (
            "Settings must expose super_admin_password (plain-text) for seed hashing"
        )
        assert settings.super_admin_password == "plaintext-secret-123"
        assert not hasattr(settings, "super_admin_password_hash"), (
            "Legacy super_admin_password_hash field must be removed; "
            "the seed now hashes the plain-text password itself"
        )

    def test_settings_super_admin_password_defaults_to_empty(self, monkeypatch):
        """Edge case: when SUPER_ADMIN_PASSWORD is absent, the field defaults to "".

        The seed uses this to skip creating an admin in dev environments.
        """
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "testsecret")
        monkeypatch.setenv("ENV", "test")
        monkeypatch.delenv("SUPER_ADMIN_PASSWORD", raising=False)

        from app.config import Settings
        settings = Settings()
        assert settings.super_admin_password == ""
