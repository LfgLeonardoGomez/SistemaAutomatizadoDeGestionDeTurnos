import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    from app.main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    from app.config import Settings
    return Settings()
