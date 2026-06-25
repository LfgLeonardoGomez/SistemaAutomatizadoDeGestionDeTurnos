import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from sqlalchemy import select

from app.models.profesional import Profesional
from app.models.paciente import Paciente
from app.models.turno import Turno
from app.services.notificacion_service import (
    obtener_turnos_para_recordar,
    enviar_recordatorio_telegram,
    marcar_recordatorio_enviado,
)


async def _seed_profesional(db_session):
    p = Profesional(
        nombre="Dr. Test",
        especialidad="Test",
        duracion_turno=30,
        horario_inicio="08:00",
        horario_fin="18:00",
        dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        telegram_bot_token="test_bot_token",
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


async def _seed_paciente(db_session, profesional_id: int, telegram_chat_id: str | None = "12345"):
    paciente = Paciente(
        nombre="Juan",
        apellido="Perez",
        dni=f"{datetime.now().timestamp()}",
        telefono="555-1234",
        telegram_chat_id=telegram_chat_id,
        profesional_id=profesional_id,
    )
    db_session.add(paciente)
    await db_session.commit()
    await db_session.refresh(paciente)
    return paciente


class TestObtenerTurnosParaRecordar:
    """Tests for obtener_turnos_para_recordar query."""

    @pytest.mark.asyncio
    async def test_turno_dentro_de_ventana_es_incluido(self, db_session):
        """Scenario: Turno CONFIRMADO dentro de 24h con recordatorio_enviado=False."""
        profesional = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, profesional.id)

        from unittest.mock import patch
        ahora = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        turno = Turno(
            fecha=ahora.date(),
            hora_inicio=(ahora + timedelta(hours=2)).time(),
            hora_fin=(ahora + timedelta(hours=2, minutes=30)).time(),
            estado="CONFIRMADO",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()

        with patch("app.services.notificacion_service.datetime") as mock_dt:
            mock_dt.now.return_value = ahora
            mock_dt.combine = datetime.combine
            mock_dt.timedelta = timedelta
            turnos = await obtener_turnos_para_recordar(db_session, profesional_id=profesional.id, horas_antes=24)
        assert len(turnos) == 1
        assert turnos[0].id == turno.id

    @pytest.mark.asyncio
    async def test_turno_fuera_de_ventana_es_excluido(self, db_session):
        """Scenario: Turno CONFIRMADO fuera de 24h es excluido."""
        profesional = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, profesional.id)

        futuro = datetime.now() + timedelta(days=2)
        turno = Turno(
            fecha=futuro.date(),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CONFIRMADO",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()

        turnos = await obtener_turnos_para_recordar(db_session, profesional_id=profesional.id, horas_antes=24)
        assert len(turnos) == 0

    @pytest.mark.asyncio
    async def test_turno_ya_recordado_es_excluido(self, db_session):
        """Scenario: Turno con recordatorio_enviado=True es excluido."""
        profesional = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, profesional.id)

        ahora = datetime.now()
        turno = Turno(
            fecha=ahora.date(),
            hora_inicio=(ahora + timedelta(hours=2)).time(),
            hora_fin=(ahora + timedelta(hours=2, minutes=30)).time(),
            estado="CONFIRMADO",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
            recordatorio_enviado=True,
        )
        db_session.add(turno)
        await db_session.commit()

        turnos = await obtener_turnos_para_recordar(db_session, profesional_id=profesional.id, horas_antes=24)
        assert len(turnos) == 0

    @pytest.mark.asyncio
    async def test_turno_no_confirmado_es_excluido(self, db_session):
        """Scenario: Turno DISPONIBLE dentro de ventana es excluido."""
        profesional = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, profesional.id)

        ahora = datetime.now()
        turno = Turno(
            fecha=ahora.date(),
            hora_inicio=(ahora + timedelta(hours=2)).time(),
            hora_fin=(ahora + timedelta(hours=2, minutes=30)).time(),
            estado="DISPONIBLE",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()

        turnos = await obtener_turnos_para_recordar(db_session, profesional_id=profesional.id, horas_antes=24)
        assert len(turnos) == 0

    @pytest.mark.asyncio
    async def test_turno_de_otro_profesional_es_excluido(self, db_session):
        """Scenario: Turno de otro profesional es excluido."""
        profesional_a = await _seed_profesional(db_session)
        profesional_b = Profesional(
            nombre="Dr. B",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
            telegram_bot_token="test_bot_token_b",
        )
        db_session.add(profesional_b)
        await db_session.commit()
        await db_session.refresh(profesional_b)

        paciente = await _seed_paciente(db_session, profesional_a.id)

        ahora = datetime.now()
        turno = Turno(
            fecha=ahora.date(),
            hora_inicio=(ahora + timedelta(hours=2)).time(),
            hora_fin=(ahora + timedelta(hours=2, minutes=30)).time(),
            estado="CONFIRMADO",
            profesional_id=profesional_a.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()

        turnos = await obtener_turnos_para_recordar(db_session, profesional_id=profesional_b.id, horas_antes=24)
        assert len(turnos) == 0


class TestEnviarRecordatorioTelegram:
    """Tests for enviar_recordatorio_telegram."""

    def setup_method(self):
        from app.services.telegram_service import _reset_state
        _reset_state()

    @pytest.mark.asyncio
    async def test_envio_exitoso_retorna_true(self, db_session):
        """Scenario: Envío exitoso de recordatorio."""
        profesional = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, profesional.id)

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CONFIRMADO",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)

        with patch("app.services.telegram_service.run_in_threadpool", new=AsyncMock()) as mock_pool:
            with patch("app.services.telegram_service._get_bot") as mock_bot:
                mock_bot_instance = MagicMock()
                mock_bot.return_value = mock_bot_instance
                ok = await enviar_recordatorio_telegram(turno, bot_token="test_token")
                assert ok is True
                mock_pool.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_envio_falla_retorna_false(self, db_session):
        """Scenario: Falla de Telegram retorna False."""
        profesional = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, profesional.id)

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CONFIRMADO",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)

        with patch("app.services.notificacion_service.enviar_mensaje", new=AsyncMock(return_value=False)):
            ok = await enviar_recordatorio_telegram(turno, bot_token="test_token")
            assert ok is False

    @pytest.mark.asyncio
    async def test_paciente_sin_chat_id_retorna_true_y_no_envia(self, db_session):
        """Scenario: Paciente sin chat_id retorna True (marca flag) pero no envía."""
        profesional = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, profesional.id, telegram_chat_id=None)

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CONFIRMADO",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)

        with patch("app.services.telegram_service.run_in_threadpool", new=AsyncMock()) as mock_pool:
            ok = await enviar_recordatorio_telegram(turno, bot_token="test_token")
            assert ok is True
            mock_pool.assert_not_awaited()


class TestMarcarRecordatorioEnviado:
    """Tests for marcar_recordatorio_enviado."""

    @pytest.mark.asyncio
    async def test_marca_recordatorio_enviado(self, db_session):
        """Scenario: Marcar recordatorio_enviado = True."""
        profesional = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, profesional.id)

        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CONFIRMADO",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)

        await marcar_recordatorio_enviado(db_session, turno.id, profesional_id=profesional.id)
        await db_session.refresh(turno)
        assert turno.recordatorio_enviado is True

    @pytest.mark.asyncio
    async def test_marcar_turno_inexistente_no_falla(self, db_session):
        """Scenario: Marcar recordatorio de turno inexistente no falla."""
        profesional = await _seed_profesional(db_session)
        await marcar_recordatorio_enviado(db_session, 99999, profesional_id=profesional.id)
        # No exception expected

    @pytest.mark.asyncio
    async def test_marcar_turno_de_otro_profesional_no_falla(self, db_session):
        """Scenario: Marcar recordatorio de turno de otro profesional no modifica nada."""
        profesional_a = await _seed_profesional(db_session)
        profesional_b = Profesional(
            nombre="Dr. B",
            especialidad="Test",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes"],
            telegram_bot_token="test_bot_token_b",
        )
        db_session.add(profesional_b)
        await db_session.commit()
        await db_session.refresh(profesional_b)

        paciente = await _seed_paciente(db_session, profesional_a.id)
        turno = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CONFIRMADO",
            profesional_id=profesional_a.id,
            paciente_id=paciente.id,
            recordatorio_enviado=False,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)

        await marcar_recordatorio_enviado(db_session, turno.id, profesional_id=profesional_b.id)
        await db_session.refresh(turno)
        assert turno.recordatorio_enviado is False
