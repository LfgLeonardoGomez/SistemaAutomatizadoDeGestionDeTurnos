import pytest
import pytest_asyncio
from collections.abc import AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import Base and all models to ensure metadata is populated
from app.models.base import Base
from app.models import paciente, profesional, turno, reserva_temporal, lista_de_espera


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    from app.main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def async_engine():
    """Create a fresh async engine for each test using StaticPool."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        future=True,
        connect_args={"check_same_thread": False},
    )

    # Enable foreign key constraints for SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session bound to the in-memory SQLite database."""
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()
