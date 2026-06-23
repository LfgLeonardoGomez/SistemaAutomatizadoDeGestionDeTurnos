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
from app.models.profesional import Profesional


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
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


@pytest_asyncio.fixture
async def profesional(db_session) -> Profesional:
    """Create and persist a Profesional with all required fields for testing."""
    from app.models.profesional import Profesional
    from app.services.auth_service import hash_password
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
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
def api_client(db_session, monkeypatch):
    """TestClient with get_db overridden to use the in-memory db_session."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")

    from app.dependencies import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    del app.dependency_overrides[get_db]


@pytest.fixture
def authenticated_client(api_client, profesional):
    """TestClient with Authorization header set via login."""
    login_payload = {
        "email": profesional.email,
        "password": "changeme",
    }
    response = api_client.post("/auth/login", json=login_payload)
    assert response.status_code == 200
    token = response.json()["access_token"]
    api_client.headers["Authorization"] = f"Bearer {token}"
    yield api_client
    del api_client.headers["Authorization"]
