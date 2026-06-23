import os
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine


class TestDatabaseConnectivity:
    """Tests for SQLAlchemy async engine and Alembic configuration."""

    def test_async_engine_creation(self, monkeypatch):
        """Scenario: Database engine initialization."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        from app.dependencies import _get_engine
        engine = _get_engine()
        assert isinstance(engine, AsyncEngine)
        assert "asyncpg" in str(engine.url)

    def test_alembic_ini_exists(self):
        """Scenario: Alembic configuration exists — alembic.ini."""
        backend_dir = Path(__file__).parent.parent
        alembic_ini = backend_dir / "alembic.ini"
        assert alembic_ini.exists(), "alembic.ini should exist"

    def test_alembic_env_py_exists(self):
        """Scenario: Alembic configuration exists — env.py."""
        backend_dir = Path(__file__).parent.parent
        env_py = backend_dir / "alembic" / "env.py"
        assert env_py.exists(), "alembic/env.py should exist"

    def test_alembic_current_runs(self, monkeypatch):
        """Scenario: Alembic current executes without unhandled exceptions."""
        import socket
        # Skip if Docker DB is not reachable
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            if sock.connect_ex(("localhost", 15432)) != 0:
                pytest.skip("Docker PostgreSQL on port 15432 is not available")
        finally:
            sock.close()

        # Use the Docker Compose PostgreSQL instance on host port 15432
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://turnos:turnos@localhost:15432/turnos")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        backend_dir = Path(__file__).parent.parent
        import subprocess
        result = subprocess.run(
            ["alembic", "current"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"Alembic failed: {result.stderr}"
        assert "Traceback" not in result.stderr, f"Unhandled exception: {result.stderr}"
