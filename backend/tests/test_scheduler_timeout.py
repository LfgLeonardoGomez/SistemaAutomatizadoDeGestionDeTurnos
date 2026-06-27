import pytest
from unittest.mock import patch, AsyncMock

from app.scheduler.jobs import _procesar_timeouts_lista_espera_job
from tests.conftest import make_profesional


async def _seed_profesional(db_session):
    p = make_profesional(especialidad="Odontología")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


class TestProcesarTimeoutsListaEsperaJob:
    @pytest.mark.asyncio
    async def test_job_ejecuta_procesar_timeouts(self, monkeypatch, db_session):
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        p = await _seed_profesional(db_session)

        with patch("app.scheduler.jobs.procesar_timeouts_lista_espera", new=AsyncMock(return_value=3)) as mock_procesar:
            await _procesar_timeouts_lista_espera_job(session=db_session)

        mock_procesar.assert_awaited_once_with(db_session, profesional_id=p.id, minutos_timeout=5)

    @pytest.mark.asyncio
    async def test_job_con_session_directa(self, monkeypatch, db_session):
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        p = await _seed_profesional(db_session)

        with patch("app.scheduler.jobs.procesar_timeouts_lista_espera", new=AsyncMock(return_value=0)) as mock_procesar:
            await _procesar_timeouts_lista_espera_job(session=db_session)

        mock_procesar.assert_awaited_once_with(db_session, profesional_id=p.id, minutos_timeout=5)
