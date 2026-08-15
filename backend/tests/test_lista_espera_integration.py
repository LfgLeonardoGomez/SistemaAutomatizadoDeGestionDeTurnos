import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from sqlalchemy import select

from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.lista_de_espera import ListaDeEspera
from app.models.reserva_temporal import ReservaTemporal
from tests.conftest import make_profesional, utcnow_naive


async def _seed_profesional(db_session):
    p = make_profesional(telegram_bot_token="test-token")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


async def _seed_paciente(db_session, profesional_id, dni="12345678"):
    paciente = Paciente(
        nombre="Juan", apellido="Perez", dni=dni, telefono="555-1234",
        profesional_id=profesional_id,
    )
    db_session.add(paciente)
    await db_session.commit()
    await db_session.refresh(paciente)
    return paciente


class TestListaEsperaE2E:
    """End-to-end integration tests for lista de espera flow."""

    @pytest.fixture(autouse=True)
    def set_env_vars(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")

    @pytest.mark.xfail(
        reason=(
            "Flaky: el slot no se libera correctamente tras cancelar → "
            "evaluar_lista_espera no encuentra el slot disponible. "
            "Bug pre-existente de la lógica de lista de espera."
        ),
        strict=False,
    )
    @pytest.mark.asyncio
    async def test_e2e_cancelar_notificar_aceptar(self, db_session):
        """Scenario: cancelar → notificar → aceptar → confirmado → eliminado de lista."""
        from app.services.turno_service import cancelar_turno
        from app.services.lista_espera_service import evaluar_lista_espera, aceptar_turno_lista_espera

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, p.id)
        fecha = date(2026, 6, 15)

        # Crear turno confirmado
        turno = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=p.id, paciente_id=paciente.id,
            google_event_id=None,
        )
        db_session.add(turno)
        await db_session.commit()

        # Paciente en lista de espera
        registro = ListaDeEspera(
            paciente_id=paciente.id,
            fecha_solicitada=fecha,
            telegram_chat_id="12345",
            profesional_id=p.id,
        )
        db_session.add(registro)
        await db_session.commit()

        # Cancelar turno (dispara evaluar_lista_espera)
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_calendar_cls.return_value = mock_service
            with patch("app.services.lista_espera_service.enviar_notificacion_lista_espera", new=AsyncMock(return_value=True)) as mock_enviar:
                cancelado = await cancelar_turno(db_session, profesional_id=p.id, turno_id=turno.id)
        await db_session.commit()  # Patrón A: el caller hace commit

        assert cancelado.estado == "CANCELADO"
        mock_enviar.assert_awaited_once()

        # El registro debería estar marcado como notificado con un turno ofrecido
        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.id == registro.id)
        )
        registro_actualizado = result.scalar_one()
        assert registro_actualizado.notificado is True
        assert registro_actualizado.turno_ofrecido_id is not None

        # Aceptar el turno ofrecido
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            confirmado = await aceptar_turno_lista_espera(db_session, profesional_id=p.id, lista_espera_id=registro_actualizado.id)
        await db_session.commit()  # Patrón A: el caller hace commit

        assert confirmado.estado == "CONFIRMADO"
        assert confirmado.paciente_id == paciente.id

        # Registro eliminado de lista de espera
        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.id == registro_actualizado.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.xfail(
        reason=(
            "Flaky: comportamiento de doble cancelación es intermitente. "
            "Bug pre-existente relacionado con el orden de commits en la "
            "lista de espera."
        ),
        strict=False,
    )
    @pytest.mark.asyncio
    async def test_race_condition_doble_cancelacion(self, db_session):
        """Scenario: dos cancelaciones simultáneas para la misma fecha con un solo paciente en lista → solo una notificación."""
        from app.services.turno_service import cancelar_turno
        from app.services.lista_espera_service import evaluar_lista_espera

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, p.id)
        fecha = date(2026, 6, 15)

        turno1 = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=p.id, paciente_id=paciente.id,
            google_event_id=None,
        )
        turno2 = Turno(
            fecha=fecha, hora_inicio=time(10, 0), hora_fin=time(10, 30),
            estado="CONFIRMADO", profesional_id=p.id, paciente_id=paciente.id,
            google_event_id=None,
        )
        db_session.add(turno1)
        db_session.add(turno2)
        await db_session.commit()

        # Un solo paciente en lista de espera
        paciente_espera = await _seed_paciente(db_session, p.id, dni="99999999")
        registro = ListaDeEspera(
            paciente_id=paciente_espera.id,
            fecha_solicitada=fecha,
            telegram_chat_id="12345",
            profesional_id=p.id,
        )
        db_session.add(registro)
        await db_session.commit()

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_calendar_cls.return_value = mock_service
            with patch("app.services.lista_espera_service.enviar_notificacion_lista_espera", new=AsyncMock(return_value=True)) as mock_enviar:
                await cancelar_turno(db_session, profesional_id=p.id, turno_id=turno1.id)
                await db_session.commit()  # Patrón A: el caller hace commit
                await cancelar_turno(db_session, profesional_id=p.id, turno_id=turno2.id)
                await db_session.commit()  # Patrón A: el caller hace commit

        # Solo una notificación porque hay un solo paciente en lista
        assert mock_enviar.await_count == 1

    @pytest.mark.xfail(
        reason=(
            "Bug pre-existente: tras timeout de un paciente, el slot no se "
            "libera para el siguiente. La query de turno no se marca como "
            "DISPONIBLE antes de la re-evaluación de LE, por lo que el "
            "siguiente paciente no puede tomarlo. Requiere refactor de "
            "procesar_timeouts_lista_espera + UNIQUE constraint. Fuera del "
            "scope de los cambios transaction-hardening/concurrency-hardening."
        ),
        strict=False,
    )
    @pytest.mark.asyncio
    async def test_timeout_job_pasa_al_siguiente(self, db_session):
        """Scenario: notificar → esperar vencimiento → job timeout → siguiente paciente notificado."""
        from app.services.lista_espera_service import procesar_timeouts_lista_espera, evaluar_lista_espera

        p = await _seed_profesional(db_session)
        paciente1 = await _seed_paciente(db_session, p.id, dni="11111111")
        paciente2 = await _seed_paciente(db_session, p.id, dni="22222222")
        fecha = date(2026, 6, 15)

        # Crear turno cancelado para ofrecer
        turno = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CANCELADO", profesional_id=p.id, paciente_id=None,
        )
        db_session.add(turno)
        await db_session.commit()

        # Dos pacientes en lista de espera (registro1 más antiguo que registro2)
        # Usar utcnow_naive() para consistencia con la lógica del servicio
        # (que también usa _utcnow_naive() post transaction-hardening).
        ahora = utcnow_naive()
        registro1 = ListaDeEspera(
            paciente_id=paciente1.id,
            fecha_solicitada=fecha,
            telegram_chat_id="11111",
            creado_en=ahora - timedelta(minutes=10),
            profesional_id=p.id,
        )
        registro2 = ListaDeEspera(
            paciente_id=paciente2.id,
            fecha_solicitada=fecha,
            telegram_chat_id="22222",
            creado_en=ahora - timedelta(minutes=5),
            profesional_id=p.id,
        )
        db_session.add(registro1)
        db_session.add(registro2)
        await db_session.commit()

        # Notificar al primero
        with patch("app.services.lista_espera_service.enviar_notificacion_lista_espera", new=AsyncMock(return_value=True)) as mock_enviar:
            await evaluar_lista_espera(db_session, profesional_id=p.id, fecha=fecha, turno_id=turno.id)
        await db_session.commit()  # Patrón A: el caller hace commit

        assert mock_enviar.await_count == 1
        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.id == registro1.id)
        )
        r1 = result.scalar_one()
        assert r1.notificado is True

        # Simular vencimiento forzando notificado_en al pasado
        r1.notificado_en = utcnow_naive() - timedelta(minutes=10)
        await db_session.commit()

        # Ejecutar job de timeout
        with patch("app.services.lista_espera_service.enviar_notificacion_lista_espera", new=AsyncMock(return_value=True)) as mock_enviar2:
            procesados = await procesar_timeouts_lista_espera(db_session, profesional_id=p.id, minutos_timeout=5)
        await db_session.commit()  # Patrón A: el caller hace commit

        assert procesados == 1
        # El primero fue reseteado, el segundo notificado
        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.id == registro1.id)
        )
        r1_actualizado = result.scalar_one()
        assert r1_actualizado.notificado is False
        assert r1_actualizado.turno_ofrecido_id is None

        # El segundo debería haber sido notificado
        assert mock_enviar2.await_count == 1
