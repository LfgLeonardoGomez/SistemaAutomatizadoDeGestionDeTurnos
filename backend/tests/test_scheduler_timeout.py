import pytest
from unittest.mock import patch, AsyncMock

from app.scheduler.jobs import _procesar_timeouts_lista_espera_job


class TestProcesarTimeoutsListaEsperaJob:
    @pytest.mark.asyncio
    async def test_job_ejecuta_procesar_timeouts(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")

        with patch("app.scheduler.jobs.procesar_timeouts_lista_espera", new=AsyncMock(return_value=3)) as mock_procesar:
            await _procesar_timeouts_lista_espera_job()

        mock_procesar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_job_con_session_directa(self, monkeypatch, db_session):
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")

        with patch("app.scheduler.jobs.procesar_timeouts_lista_espera", new=AsyncMock(return_value=0)) as mock_procesar:
            await _procesar_timeouts_lista_espera_job(session=db_session)

        mock_procesar.assert_awaited_once_with(db_session, minutos_timeout=5)
