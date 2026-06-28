import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from sqlalchemy import select
from tests.conftest import make_profesional


async def _seed_profesional(db_session):
    p = make_profesional(especialidad="Odontología")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


class TestSchedulerJob:
    @pytest.mark.asyncio
    async def test_scheduler_job_liberar_reservas_vencidas(self, db_session, monkeypatch):
        """Scenario: job ejecuta liberar_reservas_vencidas sin errores."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        from app.scheduler.jobs import _liberar_reservas_vencidas_job
        from app.services.turno_service import reservar_turno
        from app.config import Settings

        settings = Settings()

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        # Crear reserva temporal
        turno = await reservar_turno(
            db_session, profesional_id=p.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None, settings=settings
        )

        # Forzar expiración
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
        )
        reserva = result.scalar_one()
        reserva.expiracion = datetime.now() - timedelta(minutes=1)
        await db_session.commit()

        # Ejecutar el job directamente pasando la sesión de test
        await _liberar_reservas_vencidas_job(session=db_session)

        # Verificar que el turno fue liberado
        result = await db_session.execute(
            select(Turno).where(Turno.id == turno.id)
        )
        turno_actualizado = result.scalar_one()
        assert turno_actualizado.estado == "DISPONIBLE"

    @pytest.mark.asyncio
    async def test_scheduler_job_sin_vencidas(self, db_session, monkeypatch):
        """Scenario: job ejecuta sin errores cuando no hay vencidas."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        from app.scheduler.jobs import _liberar_reservas_vencidas_job

        # Ejecutar el job directamente sin reservas
        await _liberar_reservas_vencidas_job(session=db_session)
        # No debe lanzar excepciones

    @pytest.mark.asyncio
    async def test_scheduler_tiene_job_registrado(self, client):
        """Scenario: job aparece en el scheduler al startup.

        El fixture ``client`` overridea el lifespan con ``_noop_lifespan``
        (para no arrancar el scheduler en tests). Por eso instanciamos el
        scheduler directamente via ``init_scheduler(app)`` para verificar
        que los jobs se registran.

        Es async porque ``init_scheduler`` requiere un event loop activo
        (APScheduler AsyncIOScheduler).
        """
        from app.main import app
        from app.scheduler.jobs import init_scheduler

        # Si ya hay un scheduler corriendo, limpiarlo primero
        existing = getattr(app.state, "scheduler", None)
        if existing is not None:
            existing.shutdown(wait=False)
            app.state.scheduler = None

        init_scheduler(app)

        scheduler = getattr(app.state, "scheduler", None)
        assert scheduler is not None
        jobs = scheduler.get_jobs()
        job_ids = [j.id for j in jobs]
        assert "liberar_reservas_vencidas" in job_ids
        assert "marcar_turnos_completados" in job_ids
        assert "enviar_recordatorios" in job_ids
        # Cleanup: shutdown no espera a que terminen jobs en curso
        scheduler.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_scheduler_job_marcar_turnos_completados(self, db_session, monkeypatch):
        """Scenario: job ejecuta marcar_turnos_completados sin errores."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        from app.scheduler.jobs import _marcar_turnos_completados_job
        from app.models.turno import Turno
        from app.models.paciente import Paciente

        p = await _seed_profesional(db_session)
        paciente = Paciente(
            nombre="Juan", apellido="Perez", dni="12345678", telefono="555-1234",
            profesional_id=p.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        turno = Turno(
            fecha=date(2020, 1, 1),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CONFIRMADO",
            profesional_id=p.id,
            paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()

        await _marcar_turnos_completados_job(session=db_session)

        result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
        turno_db = result.scalar_one()
        assert turno_db.estado == "COMPLETADO"

    @pytest.mark.asyncio
    async def test_scheduler_job_marcar_turnos_completados_sin_candidatos(self, db_session, monkeypatch):
        """Scenario: job ejecuta sin errores cuando no hay candidatos."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        from app.scheduler.jobs import _marcar_turnos_completados_job

        await _marcar_turnos_completados_job(session=db_session)
        # No debe lanzar excepciones

    @pytest.mark.asyncio
    async def test_scheduler_job_marcar_turnos_completados_loguea_excepciones(self, db_session, monkeypatch):
        """Scenario: job loguea excepciones sin detener el scheduler.

        Mockeamos ``_ejecutar_marcar_turnos_completados`` (no
        ``marcar_turnos_completados``) porque el try/except interior
        hace ``await sess.rollback()`` que falla con ``MissingGreenlet``
        cuando la sesión fue tocada por un mock sync. Patcheando el
        ejecutor evitamos ese side-effect no relacionado al test.

        Mockeamos el logger directamente porque caplog en pytest-asyncio
        con event loop reutilizado (suite completa) no captura los records
        del logger específico. El patrón es el mismo que
        ``test_enviar_mensaje_con_log_loggea_contexto_al_fallar``.
        """
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        from app.scheduler.jobs import _marcar_turnos_completados_job
        from unittest.mock import patch

        p = await _seed_profesional(db_session)

        async def _raise_runtime_error(*args, **kwargs):
            raise RuntimeError("DB error")

        with patch("app.scheduler.jobs._ejecutar_marcar_turnos_completados", side_effect=_raise_runtime_error):
            with patch("app.scheduler.jobs.logger") as mock_logger:
                await _marcar_turnos_completados_job(session=db_session)

                # La excepción se captura en el try/except exterior. El
                # mensaje exacto es "Error en job marcar_turnos_completados: {exc}".
                assert mock_logger.exception.called
                call_args = mock_logger.exception.call_args
                assert "Error en job marcar_turnos_completados" in call_args[0][0]
                assert "DB error" in call_args[0][0]

    # -----------------------------------------------------------------------
    # _enviar_recordatorios_job
    # -----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_scheduler_job_enviar_recordatorios_dos_turnos(self, db_session, monkeypatch):
        """Scenario: job encuentra 2 turnos y envía 2 mensajes."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        from app.scheduler.jobs import _enviar_recordatorios_job
        from app.models.paciente import Paciente
        from app.models.turno import Turno

        p = await _seed_profesional(db_session)
        paciente = Paciente(
            nombre="Juan", apellido="Perez", dni="11111111", telefono="555-1234",
            telegram_chat_id="12345",
            profesional_id=p.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        # Crear 2 turnos a 1h y 1h10m en el futuro desde AHORA (no hora
        # fija) para evitar problemas de TZ y para garantizar que estén
        # dentro de la ventana ``horas_antes=24`` del job.
        from unittest.mock import patch
        base_dt = datetime.now() + timedelta(hours=1)
        for i in range(2):
            turno = Turno(
                fecha=base_dt.date(),
                hora_inicio=(base_dt + timedelta(minutes=i * 10)).time(),
                hora_fin=(base_dt + timedelta(minutes=i * 10 + 30)).time(),
                estado="CONFIRMADO",
                profesional_id=p.id,
                paciente_id=paciente.id,
                recordatorio_enviado=False,
            )
            db_session.add(turno)
        await db_session.commit()

        with patch("app.scheduler.jobs.enviar_recordatorio_telegram", new=AsyncMock(return_value=True)) as mock_enviar:
            await _enviar_recordatorios_job(session=db_session)
            assert mock_enviar.await_count == 2

        # Verificar que los turnos fueron marcados
        result = await db_session.execute(select(Turno).where(Turno.paciente_id == paciente.id))
        turnos = result.scalars().all()
        assert all(t.recordatorio_enviado is True for t in turnos)

    @pytest.mark.asyncio
    async def test_scheduler_job_enviar_recordatorios_sin_candidatos(self, db_session, monkeypatch):
        """Scenario: job no encuentra turnos y no envía nada."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        from app.scheduler.jobs import _enviar_recordatorios_job

        with patch("app.scheduler.jobs.enviar_recordatorio_telegram", new=AsyncMock(return_value=True)) as mock_enviar:
            await _enviar_recordatorios_job(session=db_session)
            assert mock_enviar.await_count == 0

    @pytest.mark.asyncio
    async def test_scheduler_job_enviar_recordatorios_maneja_excepcion(self, db_session, monkeypatch):
        """Scenario: job maneja excepción de Telegram sin detenerse.

        Mockeamos el logger directamente porque caplog en pytest-asyncio
        con event loop reutilizado (suite completa) no captura los records
        del logger específico. El patrón es el mismo que
        ``test_enviar_mensaje_con_log_loggea_contexto_al_fallar``.
        """
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        from app.scheduler.jobs import _enviar_recordatorios_job
        from app.models.paciente import Paciente
        from app.models.turno import Turno

        p = await _seed_profesional(db_session)
        paciente = Paciente(
            nombre="Juan", apellido="Perez", dni="22222222", telefono="555-1234",
            telegram_chat_id="12345",
            profesional_id=p.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        # Crear un turno a 1h en el futuro desde AHORA (no hora fija) para
        # evitar problemas de TZ. El filtro ``ahora <= dt <= limite`` de
        # ``obtener_turnos_para_recordar`` requiere que el turno esté
        # estrictamente en el futuro, así que ``+1h`` es seguro.
        base_dt = datetime.now() + timedelta(hours=1)
        turno = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=30)).time(),
            estado="CONFIRMADO",
            profesional_id=p.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()

        with patch("app.scheduler.jobs.enviar_recordatorio_telegram", new=AsyncMock(side_effect=Exception("Telegram fail"))) as mock_enviar:
            with patch("app.scheduler.jobs.logger") as mock_logger:
                await _enviar_recordatorios_job(session=db_session)
                assert mock_enviar.await_count == 1

                # El mensaje exacto logueado es
                # "Error enviando recordatorio para turno {turno_id}: {exc}".
                assert mock_logger.error.called
                call_args = mock_logger.error.call_args
                assert "Error enviando recordatorio" in call_args[0][0]
                assert f"turno {turno.id}" in call_args[0][0]
                assert "Telegram fail" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_scheduler_job_enviar_recordatorios_e2e(self, db_session, monkeypatch):
        """Scenario: crear turno CONFIRMADO dentro de 24h → ejecutar job → verificar mock y flag."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        from app.scheduler.jobs import _enviar_recordatorios_job
        from app.models.paciente import Paciente
        from app.models.turno import Turno
        from sqlalchemy import select

        p = await _seed_profesional(db_session)
        paciente = Paciente(
            nombre="Juan", apellido="Perez", dni="33333333", telefono="555-1234",
            telegram_chat_id="12345",
            profesional_id=p.id,
        )
        db_session.add(paciente)
        await db_session.commit()

        # Usar HOY con hora 23:00 para evitar cruce de medianoche.
        # Turno a 1h en el futuro desde AHORA (no hora fija) para evitar
        # problemas de TZ y garantizar que esté dentro de la ventana.
        base_dt = datetime.now() + timedelta(hours=1)
        turno = Turno(
            fecha=base_dt.date(),
            hora_inicio=base_dt.time(),
            hora_fin=(base_dt + timedelta(minutes=30)).time(),
            estado="CONFIRMADO",
            profesional_id=p.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()

        with patch("app.scheduler.jobs.enviar_recordatorio_telegram", new=AsyncMock(return_value=True)) as mock_enviar:
            await _enviar_recordatorios_job(session=db_session)
            assert mock_enviar.await_count == 1

        result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
        turno_db = result.scalar_one()
        assert turno_db.recordatorio_enviado is True
