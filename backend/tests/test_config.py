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


class TestEnvExampleCompleteness:
    """Spec: Single canonical .env.example at repository root.

    Validates the .env.example files in the repo are coherent with
    `backend/app/config.py`. This is the automated check for task 2.3.
    """

    @staticmethod
    def _repo_root() -> str:
        """Absolute path to the repository root (parent of backend/)."""
        from pathlib import Path
        return str(Path(__file__).resolve().parent.parent.parent)

    @classmethod
    def _root_env_example(cls) -> str:
        from pathlib import Path
        return str(Path(cls._repo_root()) / ".env.example")

    @classmethod
    def _backend_env_example(cls) -> str:
        from pathlib import Path
        return str(Path(cls._repo_root()) / "backend" / ".env.example")

    @staticmethod
    def _parse_env_example(path: str) -> set[str]:
        """Return uppercase env var names declared in an .env.example file.

        Lines starting with '#' and blank lines are ignored. Inline comments
        after a value are not stripped (we only care about the var name, which
        is the substring before the first '=').
        """
        import os
        names: set[str] = set()
        if not os.path.isfile(path):
            return names
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in stripped:
                    continue
                name = stripped.split("=", 1)[0].strip()
                if name:
                    names.add(name.upper())
        return names

    def test_no_env_example_inside_backend(self):
        """Spec: .env.example lives at the repository root only.

        Scenario: there is no .env.example inside backend/ (broken source of
        truth pre-cleanup).
        """
        import os
        assert not os.path.isfile(self._backend_env_example()), (
            "backend/.env.example must not exist; "
            "the canonical .env.example lives at the repo root only"
        )

    def test_root_env_example_exists(self):
        """Spec: .env.example exists at the repo root."""
        import os
        assert os.path.isfile(self._root_env_example()), (
            ".env.example must exist at the repo root"
        )

    def test_root_env_example_matches_settings_fields(self):
        """Spec: .env.example contains every variable declared in config.py.

        We compare the set of variable names in .env.example against the
        declared fields on `Settings`. Names are uppercased to match the
        env-var convention. Fields with uppercase-only chars are taken as-is.
        """
        from app.config import Settings
        declared = set()
        for name, field in Settings.model_fields.items():
            env_name = (field.alias or name).upper()
            declared.add(env_name)

        declared_in_example = self._parse_env_example(self._root_env_example())
        missing = declared - declared_in_example
        extra = declared_in_example - declared

        assert not missing, (
            f"Variables declared in config.py but missing from .env.example: {sorted(missing)}"
        )
        assert not extra, (
            f"Variables in .env.example but not declared in config.py: {sorted(extra)}"
        )


class TestDockerComposeBackendEnvironment:
    """Spec: docker-compose.yml injects all critical backend variables.

    The `backend` service must declare every environment variable required by
    `backend/app/config.py` in its `environment` block, either as a literal
    value or as a `${VAR:-default}` shell-style fallback.
    """

    @staticmethod
    def _compose_path() -> str:
        from pathlib import Path
        return str(Path(__file__).resolve().parent.parent.parent / "docker-compose.yml")

    @staticmethod
    def _load_compose_backend_environment() -> dict:
        import yaml
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent.parent / "docker-compose.yml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        services = data.get("services", {}) or {}
        backend = services.get("backend", {}) or {}
        env = backend.get("environment", {}) or {}
        if isinstance(env, list):
            # Compose supports list form ("VAR=value" entries) — normalise to dict.
            env = dict(item.split("=", 1) for item in env if "=" in item)
        return env

    def test_docker_compose_exists(self):
        """Sanity: docker-compose.yml exists at repo root."""
        import os
        assert os.path.isfile(self._compose_path()), (
            "docker-compose.yml must exist at the repo root"
        )

    def test_docker_compose_backend_declares_all_config_vars(self):
        """Spec: backend service declares every variable from config.py.

        Each required env var must appear as a key in the `backend.environment`
        block. The value can be literal or a `${VAR:-default}` reference.
        """
        from app.config import Settings
        required = set()
        for name, field in Settings.model_fields.items():
            required.add((field.alias or name).upper())

        env = self._load_compose_backend_environment()
        declared = {k.upper() for k in env.keys()}
        missing = required - declared

        assert not missing, (
            "docker-compose.yml service 'backend' is missing env vars "
            f"required by config.py: {sorted(missing)}"
        )


class TestEnvExampleLoadsIntoSettings:
    """Spec: Settings() loads correctly with the canonical .env.example values.

    This is the automated check for task 6.2: we feed the .env.example into
    Settings() and assert that all fields are populated without error.
    """

    @staticmethod
    def _apply_env_example_to_environ(monkeypatch) -> None:
        """Load .env.example into os.environ via monkeypatch.

        Required vars (no default in Settings) are populated with safe
        stand-ins so the Settings() constructor doesn't raise.
        """
        from pathlib import Path
        env_path = Path(__file__).resolve().parent.parent.parent / ".env.example"
        # Required keys (no default in Settings) get a non-empty placeholder.
        required_placeholders = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "SECRET_KEY": "testsecret-from-env-example-check",
        }
        for key, value in required_placeholders.items():
            monkeypatch.setenv(key, value)
        # Read .env.example line by line, set everything else verbatim.
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                name, _, value = stripped.partition("=")
                name = name.strip()
                value = value.strip()
                if not name:
                    continue
                monkeypatch.setenv(name, value)

    def test_settings_loads_with_env_example_values(self, monkeypatch):
        """Spec: Settings() loads with every value defined in .env.example."""
        self._apply_env_example_to_environ(monkeypatch)

        from app.config import Settings
        settings = Settings()

        # Spot-check the values the .env.example explicitly sets.
        assert settings.database_url.startswith("postgresql+asyncpg://")
        assert settings.env == "development"
        assert settings.secret_key == "change-me-in-production"
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 1440
        assert settings.reserva_temporal_minutos == 10
        assert settings.lista_espera_minutos == 5
        assert settings.recordatorio_horas_antes == 24
        assert settings.recordatorio_job_interval_minutos == 60
        assert settings.completado_job_interval_minutos == 5
        assert settings.google_calendar_max_retries == 3
        assert settings.google_calendar_base_delay == 1.0
        assert settings.google_calendar_max_delay == 10.0
        # Vars that are not in the cleaned-up .env.example must still default
        # to the empty string (not raise).
        assert settings.super_admin_password == ""
