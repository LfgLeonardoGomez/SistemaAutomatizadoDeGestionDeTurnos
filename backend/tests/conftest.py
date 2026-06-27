"""Test configuration: PostgreSQL fixtures, testcontainers fallback, cleanup.

This conftest is the source of truth for test infrastructure. Per the project's
hard rule "NADA DE SQLITE, TODO CON POSTGRESQL" no test may rely on SQLite
in-memory; all tests run against a real PostgreSQL instance.

Resolution order for the test database:
1. ``TEST_DATABASE_URL`` env var (e.g. ``postgresql+asyncpg://...``) — useful
   for local development against a manually-managed PG or the project's
   ``docker compose up db``.
2. ``testcontainers[postgres]`` — auto-managed, ephemeral PG container
   (default, requires Docker on PATH).

Schema is created via ``alembic upgrade head`` (session-scoped) and tables
are truncated between tests to keep isolation fast.
"""
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from typing import Optional

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Import Base and all models so metadata is fully populated.
from app.models.base import Base
from app.models import (
    paciente,
    profesional,
    turno,
    reserva_temporal,
    lista_de_espera,
    super_admin,
)
from app.models.profesional import Profesional
from app.services.auth_service import hash_password


# Module-level handle for the testcontainers PG container so it survives across
# the whole pytest session and can be stopped on finalizer.
_postgres_container: Optional[object] = None


def _resolve_test_database_url() -> str:
    """Pick the test database URL (testcontainers fallback to TEST_DATABASE_URL)."""
    global _postgres_container

    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url:
        return test_url

    from testcontainers.postgres import PostgresContainer

    _postgres_container = PostgresContainer("postgres:15-alpine")
    _postgres_container.start()
    sync_url = _postgres_container.get_connection_url()
    # testcontainers returns ``postgresql+psycopg2://``; swap to asyncpg.
    return sync_url.replace("postgresql+psycopg2", "postgresql+asyncpg", 1)


def _to_sync_url(async_url: str) -> str:
    """Convert a +asyncpg URL to a +psycopg URL (Alembic runs sync)."""
    return async_url.replace("+asyncpg", "+psycopg", 1)


def _run_alembic_upgrade(database_url: str) -> None:
    """Apply migrations to the test database programmatically."""
    from alembic.config import Config
    from alembic import command

    sync_url = _to_sync_url(database_url)
    os.environ["DATABASE_URL"] = sync_url

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_cfg, "head")


async def _truncate_all_tables(engine) -> None:
    """Truncate every public table and reset identity sequences."""
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        tables = [row[0] for row in result.fetchall()]
        if not tables:
            return
        quoted = ", ".join(f'"{t}"' for t in tables)
        await conn.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))


@asynccontextmanager
async def _noop_lifespan(app: FastAPI):
    """Lifespan no-op for tests: keeps scheduler off and skips seed."""
    yield


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Resolve test DB URL once per session, applying Alembic migrations."""
    url = _resolve_test_database_url()
    _run_alembic_upgrade(url)
    return url


@pytest_asyncio.fixture(scope="session")
async def engine(test_database_url: str):
    """Async engine bound to the test PostgreSQL (NullPool, no shared conns)."""
    eng = create_async_engine(test_database_url, poolclass=NullPool, future=True)
    yield eng
    await eng.dispose()
    global _postgres_container
    if _postgres_container is not None:
        _postgres_container.stop()
        _postgres_container = None


# ---------------------------------------------------------------------------
# Function-scoped fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test AsyncSession; TRUNCATE all tables after teardown."""
    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session
    await _truncate_all_tables(engine)


@pytest_asyncio.fixture
async def profesional(db_session) -> Profesional:
    """Create and persist a Profesional with all required fields for testing."""
    p = Profesional(
        nombre="Dr. Test",
        especialidad="Odontología general",
        duracion_turno=30,
        horario_inicio="08:00",
        horario_fin="18:00",
        dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        email="test@local.dev",
        password_hash=hash_password("changeme"),
        is_active=True,
        google_calendar_id="primary",
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
def client(test_database_url, db_session, monkeypatch):
    """TestClient with get_db overridden to use the test session.

    The app's lifespan is replaced with a no-op so:
    - The APScheduler is NOT started in tests (avoids background jobs
      mutating the test DB while a test is in flight).
    - The seed function does NOT run on startup (avoids creating a
      default ``Dr. Por Defecto`` Profesional that would interfere with
      tests asserting on the Profesional table state, e.g.
      ``test_seed_creates_profesional_when_empty``).
    """
    sync_url = _to_sync_url(test_database_url)
    monkeypatch.setenv("DATABASE_URL", sync_url)
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")

    from app.dependencies import _reset_engine_and_sessionmaker
    _reset_engine_and_sessionmaker()

    from app.dependencies import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    del app.dependency_overrides[get_db]
    _reset_engine_and_sessionmaker()


@pytest.fixture
def api_client(client):
    """Alias for ``client`` — preserved for tests written against the old
    conftest that imported ``api_client``. Both refer to the same TestClient
    with the ``get_db`` override installed.
    """
    return client


@pytest.fixture
def authenticated_client(client, profesional):
    """TestClient with ``Authorization: Bearer <token>`` set via login."""
    login_payload = {
        "email": profesional.email,
        "password": "changeme",
    }
    response = client.post("/auth/login", json=login_payload)
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    del client.headers["Authorization"]
