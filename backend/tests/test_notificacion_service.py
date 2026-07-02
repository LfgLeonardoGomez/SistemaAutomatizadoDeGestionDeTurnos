import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from sqlalchemy import select

from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.turno_destinatario import TurnoDestinatario
from app.services.notificacion_service import (
    obtener_turnos_para_recordar,
    enviar_recordatorio_telegram,
    marcar_recordatorio_enviado,
)
from tests.conftest import make_profesional


async def _seed_profesional(db_session):
    p = make_profesional(telegram_bot_token="test_bot_token")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


async def _seed_paciente(db_session, profesional_id: int):
    """Crea un Paciente sin telegram_chat_id (columna eliminada en C-23)."""
    paciente = Paciente(
        nombre="Juan",
        apellido="Perez",
        dni=f"{datetime.now().timestamp()}",
        telefono="555-1234",
        profesional_id=profesional_id,
    )
    db_session.add(paciente)
    await db_session.commit()
    await db_session.refresh(paciente)
    return paciente


async def _add_destinatario_telegram(db_session, turno_id: int, chat_id: str) -> TurnoDestinatario:
    """Helper: agrega un destinatario TELEGRAM al turno."""
    dest = TurnoDestinatario(
        turno_id=turno_id,
        canal="TELEGRAM",
        destinatario=chat_id,
    )
    db_session.add(dest)
    await db_session.commit()
    await db_session.refresh(dest)
    return dest


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

        # Usar un offset para evitar que la hora cruce medianoche y viole
        # ``ck_turno_horario_valido`` en zonas horarias no-UTC.
        ahora = datetime.now() - timedelta(hours=4)
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

        # Usar un offset para evitar que la hora cruce medianoche y viole
        # ``ck_turno_horario_valido`` en zonas horarias no-UTC.
        ahora = datetime.now() - timedelta(hours=4)
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
        profesional_b = make_profesional(
            nombre="Dr. B",
            dias_atencion=["Lunes"],
            telegram_bot_token="test_bot_token_b",
        )
        db_session.add(profesional_b)
        await db_session.commit()
        await db_session.refresh(profesional_b)

        paciente = await _seed_paciente(db_session, profesional_a.id)

        # Usar un offset para evitar que la hora cruce medianoche y viole
        # ``ck_turno_horario_valido`` en zonas horarias no-UTC.
        ahora = datetime.now() - timedelta(hours=4)
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
    """Tests for enviar_recordatorio_telegram.

    C-23: el recordatorio se envía al destinatario TELEGRAM del turno
    (``turno.destinatarios`` filtrado por canal), no a ``paciente.telegram_chat_id``
    (columna eliminada por ser código muerto).
    """

    def setup_method(self):
        from app.services.telegram_service import _reset_state
        _reset_state()

    @pytest.mark.asyncio
    async def test_envio_exitoso_retorna_true(self, db_session):
        """Scenario: Turno con destinatario TELEGRAM → envío exitoso retorna True."""
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
        # C-23: el chat_id vive en TurnoDestinatario, no en paciente
        await _add_destinatario_telegram(db_session, turno.id, "555001")
        # Refrescar la relación ``destinatarios`` con selectin (lazy="selectin"
        # no carga automáticamente en ``refresh()`` sin attribute_names).
        await db_session.refresh(turno, attribute_names=["destinatarios"])

        with patch("app.services.telegram_service.run_in_threadpool", new=AsyncMock()) as mock_pool:
            with patch("app.services.telegram_service._get_bot") as mock_bot:
                mock_bot_instance = MagicMock()
                mock_bot.return_value = mock_bot_instance
                ok = await enviar_recordatorio_telegram(turno, bot_token="test_token")
                assert ok is True
                mock_pool.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_envio_falla_retorna_false(self, db_session):
        """Scenario: Turno con destinatario TELEGRAM + envío que falla → retorna False."""
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
        # C-23: el chat_id vive en TurnoDestinatario
        await _add_destinatario_telegram(db_session, turno.id, "555002")
        await db_session.refresh(turno, attribute_names=["destinatarios"])

        with patch("app.services.notificacion_service.enviar_mensaje", new=AsyncMock(return_value=False)):
            ok = await enviar_recordatorio_telegram(turno, bot_token="test_token")
            assert ok is False

    @pytest.mark.asyncio
    async def test_turno_sin_destinatario_telegram_retorna_true_y_no_envia(self, db_session):
        """Scenario: Turno sin destinatario TELEGRAM → retorna True (marca flag) sin enviar.

        C-23 (TAREA 8.4): cubre el caso "turno legacy sin destinatario" o
        "confirmación administrativa sin chat". El comportamiento esperado es
        el mismo que antes (True + no envío + warning) para no romper flujos
        manuales. NO debe leer paciente.telegram_chat_id (esa columna no
        existe más).
        """
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
        await db_session.refresh(turno, attribute_names=["destinatarios"])
        # NO se agrega destinatario TELEGRAM al turno

        with patch("app.services.telegram_service.run_in_threadpool", new=AsyncMock()) as mock_pool:
            with patch("app.services.notificacion_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
                ok = await enviar_recordatorio_telegram(turno, bot_token="test_token")
                assert ok is True
                mock_pool.assert_not_awaited()
                mock_enviar.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_envio_dirigido_al_chat_del_turno_no_del_paciente(self, db_session):
        """Scenario (C-23 TAREA 8.5): dos turnos del mismo DNI con chats distintos
        reciben recordatorios en su chat respectivo (multi-chat por turno)."""
        from app.services.telegram_service import _reset_state
        _reset_state()

        profesional = await _seed_profesional(db_session)
        # Mismo DNI, mismo paciente (un DNI = una persona)
        paciente = await _seed_paciente(db_session, profesional.id)

        turno_a = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="CONFIRMADO",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
        )
        turno_b = Turno(
            fecha=date(2026, 6, 15),
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
            estado="CONFIRMADO",
            profesional_id=profesional.id,
            paciente_id=paciente.id,
        )
        db_session.add_all([turno_a, turno_b])
        await db_session.commit()
        await db_session.refresh(turno_a)
        await db_session.refresh(turno_b)
        # Dos chats distintos para el mismo paciente (Telegram chat_id son
        # siempre numéricos en producción; usamos valores distintos para
        # verificar el direccionamiento por turno).
        await _add_destinatario_telegram(db_session, turno_a.id, "111111")
        await _add_destinatario_telegram(db_session, turno_b.id, "222222")
        # Refrescar la relación destinatarios de cada turno
        await db_session.refresh(turno_a, attribute_names=["destinatarios"])
        await db_session.refresh(turno_b, attribute_names=["destinatarios"])

        # Capturamos los chat_id que recibe ``enviar_mensaje`` en cada llamada
        chats_enviados: list[int] = []

        async def _fake_enviar_mensaje(chat_id, mensaje, bot_token, keyboard=None):
            chats_enviados.append(chat_id)
            return True

        with patch("app.services.notificacion_service.enviar_mensaje", side_effect=_fake_enviar_mensaje):
            ok_a = await enviar_recordatorio_telegram(turno_a, bot_token="test_token")
            ok_b = await enviar_recordatorio_telegram(turno_b, bot_token="test_token")

        assert ok_a is True
        assert ok_b is True
        assert chats_enviados == [111111, 222222], (
            f"C-23 multi-chat: cada turno debe enviarse a SU chat, no al del otro. "
            f"Recibido: {chats_enviados}"
        )


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
        await db_session.commit()  # Patrón A: el caller hace commit
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
        profesional_b = make_profesional(
            nombre="Dr. B",
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
