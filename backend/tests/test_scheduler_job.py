import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.models.profesional import Profesional
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from sqlalchemy import select


async def _seed_profesional(db_session):
    p = Profesional(
        nombre="Dr. Test",
        especialidad="Odontología",
        duracion_turno=30,
        horario_inicio="08:00",
        horario_fin="18:00",
        dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


class TestSchedulerJob:
    @pytest.mark.asyncio
    async def test_scheduler_job_liberar_reservas_vencidas(self, db_session, monkeypatch):
        """Scenario: job ejecuta liberar_reservas_vencidas sin errores."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")

        from app.scheduler.jobs import _liberar_reservas_vencidas_job
        from app.services.turno_service import reservar_turno
        from app.config import Settings

        settings = Settings()

        p = await _seed_profesional(db_session)
        fecha = date(2026, 6, 15)

        # Crear reserva temporal
        turno = await reservar_turno(
            db_session, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None, settings=settings
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
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")

        from app.scheduler.jobs import _liberar_reservas_vencidas_job

        # Ejecutar el job directamente sin reservas
        await _liberar_reservas_vencidas_job(session=db_session)
        # No debe lanzar excepciones

    def test_scheduler_tiene_job_registrado(self, client):
        """Scenario: job aparece en el scheduler al startup."""
        from app.main import app
        scheduler = getattr(app.state, "scheduler", None)
        assert scheduler is not None
        jobs = scheduler.get_jobs()
        job_ids = [j.id for j in jobs]
        assert "liberar_reservas_vencidas" in job_ids
        assert "marcar_turnos_completados" in job_ids
        assert "enviar_recordatorios" in job_ids

    @pytest.mark.asyncio
    async def test_scheduler_job_marcar_turnos_completados(self, db_session, monkeypatch):
        """Scenario: job ejecuta marcar_turnos_completados sin errores."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")

        from app.scheduler.jobs import _marcar_turnos_completados_job
        from app.models.turno import Turno
        from app.models.paciente import Paciente

        p = await _seed_profesional(db_session)
        paciente = Paciente(
            nombre="Juan", apellido="Perez", dni="12345678", telefono="555-1234"
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
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")

        from app.scheduler.jobs import _marcar_turnos_completados_job

        await _marcar_turnos_completados_job(session=db_session)
        # No debe lanzar excepciones

    @pytest.mark.asyncio
    async def test_scheduler_job_marcar_turnos_completados_loguea_excepciones(self, db_session, monkeypatch, caplog):
        """Scenario: job loguea excepciones sin detener el scheduler."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")

        from app.scheduler.jobs import _marcar_turnos_completados_job
        import logging

        with caplog.at_level(logging.ERROR):
            # Pasar None como session forzará que el job intente crear una sesión
            # con _get_sessionmaker, que fallará porque no hay DB real.
            # Sin embargo, la excepción debe ser capturada y logueada.
            # Para testear esto de forma controlada, mockeamos marcar_turnos_completados
            from unittest.mock import patch
            with patch("app.scheduler.jobs.marcar_turnos_completados", side_effect=RuntimeError("DB error")):
                await _marcar_turnos_completados_job(session=db_session)

        assert "Error en job marcar_turnos_completados" in caplog.text

    # -----------------------------------------------------------------------
    # _enviar_recordatorios_job
    # -----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_scheduler_job_enviar_recordatorios_dos_turnos(self, db_session, monkeypatch):
        """Scenario: job encuentra 2 turnos y envía 2 mensajes."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")

        from app.scheduler.jobs import _enviar_recordatorios_job
        from app.models.paciente import Paciente
        from app.models.turno import Turno

        p = await _seed_profesional(db_session)
        paciente = Paciente(
            nombre="Juan", apellido="Perez", dni="11111111", telefono="555-1234",
            telegram_chat_id="12345",
        )
        db_session.add(paciente)
        await db_session.commit()

        ahora = datetime.now()
        for i in range(2):
            turno = Turno(
                fecha=ahora.date(),
                hora_inicio=(ahora + timedelta(hours=i + 1)).time(),
                hora_fin=(ahora + timedelta(hours=i + 1, minutes=30)).time(),
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
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")

        from app.scheduler.jobs import _enviar_recordatorios_job

        with patch("app.scheduler.jobs.enviar_recordatorio_telegram", new=AsyncMock(return_value=True)) as mock_enviar:
            await _enviar_recordatorios_job(session=db_session)
            assert mock_enviar.await_count == 0

    @pytest.mark.asyncio
    async def test_scheduler_job_enviar_recordatorios_maneja_excepcion(self, db_session, monkeypatch, caplog):
        """Scenario: job maneja excepción de Telegram sin detenerse."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")

        from app.scheduler.jobs import _enviar_recordatorios_job
        from app.models.paciente import Paciente
        from app.models.turno import Turno
        import logging

        p = await _seed_profesional(db_session)
        paciente = Paciente(
            nombre="Juan", apellido="Perez", dni="22222222", telefono="555-1234",
            telegram_chat_id="12345",
        )
        db_session.add(paciente)
        await db_session.commit()

        ahora = datetime.now()
        turno = Turno(
            fecha=ahora.date(),
            hora_inicio=(ahora + timedelta(hours=1)).time(),
            hora_fin=(ahora + timedelta(hours=1, minutes=30)).time(),
            estado="CONFIRMADO",
            profesional_id=p.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()

        with caplog.at_level(logging.ERROR):
            with patch("app.scheduler.jobs.enviar_recordatorio_telegram", new=AsyncMock(side_effect=Exception("Telegram fail"))) as mock_enviar:
                await _enviar_recordatorios_job(session=db_session)
                assert mock_enviar.await_count == 1

        assert "Error enviando recordatorio" in caplog.text

    @pytest.mark.asyncio
    async def test_scheduler_job_enviar_recordatorios_e2e(self, db_session, monkeypatch):
        """Scenario: crear turno CONFIRMADO dentro de 24h → ejecutar job → verificar mock y flag."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")

        from app.scheduler.jobs import _enviar_recordatorios_job
        from app.models.paciente import Paciente
        from app.models.turno import Turno
        from sqlalchemy import select

        p = await _seed_profesional(db_session)
        paciente = Paciente(
            nombre="Juan", apellido="Perez", dni="33333333", telefono="555-1234",
            telegram_chat_id="12345",
        )
        db_session.add(paciente)
        await db_session.commit()

        ahora = datetime.now()
        turno = Turno(
            fecha=ahora.date(),
            hora_inicio=(ahora + timedelta(hours=2)).time(),
            hora_fin=(ahora + timedelta(hours=2, minutes=30)).time(),
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
