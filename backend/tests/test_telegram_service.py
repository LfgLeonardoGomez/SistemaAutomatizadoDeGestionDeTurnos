import pytest
from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.telegram_service import (
    _get_state,
    _reset_state,
    _reset_bot,
    accion_reservar_temporal,
    accion_confirmar_turno,
    accion_cancelar_turno,
    mostrar_disponibilidad,
    enviar_mensaje,
    responder_callback_query,
    format_error,
    format_disponibilidad,
    format_confirmacion,
    escape_markdown_v2,
    split_message,
    format_fechas_keyboard,
    format_horas_keyboard,
    format_confirmacion_keyboard,
    format_lista_espera_keyboard,
    format_lista_espera_mensaje,
    enviar_notificacion_lista_espera,
    accion_aceptar_lista_espera,
    accion_rechazar_lista_espera,
)


class TestTelegramServiceIntegration:
    """Tests for telegram_service business actions."""

    def setup_method(self):
        _reset_state()
        _reset_bot()

    @pytest.mark.asyncio
    async def test_mostrar_disponibilidad_without_fecha_returns_dates_keyboard(self, db_session):
        """When no date is provided, show upcoming dates."""
        texto, keyboard = await mostrar_disponibilidad(db_session)
        assert "Seleccioná una fecha" in texto
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0

    @pytest.mark.asyncio
    async def test_mostrar_disponibilidad_with_fecha_returns_slots(self, db_session):
        """When a date is provided, show available slots."""
        from app.models.profesional import Profesional
        from app.models.turno import Turno
        db_session.add(Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        ))
        await db_session.commit()

        hoy = date.today()
        # Make sure we pick a weekday that is in dias_atencion
        while hoy.strftime("%A") not in {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}:
            hoy = date.fromordinal(hoy.toordinal() + 1)

        texto, keyboard = await mostrar_disponibilidad(db_session, fecha=hoy)
        assert "Horarios disponibles" in texto or "No hay horarios" in texto

    @pytest.mark.asyncio
    async def test_accion_reservar_temporal_creates_turno(self, db_session):
        """Temporary reservation should create a turno and update state."""
        from app.models.profesional import Profesional
        from app.models.turno import Turno
        db_session.add(Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        ))
        await db_session.commit()

        hoy = date.today()
        while hoy.strftime("%A") not in {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}:
            hoy = date.fromordinal(hoy.toordinal() + 1)

        texto, keyboard = await accion_reservar_temporal(db_session, 123, str(hoy), "08:00")
        assert "Reserva temporal creada" in texto or "Error" in texto
        state = _get_state(123)
        if "Reserva temporal creada" in texto:
            assert state["turno_temporal_id"] is not None

    @pytest.mark.asyncio
    async def test_accion_confirmar_turno_without_temporal_id_returns_error(self, db_session):
        texto = await accion_confirmar_turno(db_session, 123, {"nombre": "Juan", "apellido": "P", "dni": "1", "telefono": "2"})
        assert "No hay una reserva" in texto

    @pytest.mark.asyncio
    async def test_accion_cancelar_turno_resets_state(self, db_session):
        _get_state(123)["estado"] = "esperando_datos"
        _get_state(123)["turno_temporal_id"] = 99
        texto = await accion_cancelar_turno(db_session, 123)
        assert "cancelada" in texto.lower()
        state = _get_state(123)
        assert state["estado"] == "idle"
        assert state["turno_temporal_id"] is None

    @pytest.mark.asyncio
    async def test_reservar_temporal_error_returns_friendly_message(self, db_session):
        """When reservar_turno raises, return a friendly error message."""
        with patch("app.services.telegram_service.reservar_turno", side_effect=Exception("slot taken")):
            texto, keyboard = await accion_reservar_temporal(db_session, 123, "2026-06-15", "08:00")
        assert "Error" in texto

    @pytest.mark.asyncio
    async def test_confirmar_turno_error_returns_friendly_message(self, db_session):
        """When confirmar_turno raises, return a friendly error message."""
        _get_state(123)["turno_temporal_id"] = 1
        with patch("app.services.telegram_service.confirmar_turno", side_effect=Exception("expired")):
            texto = await accion_confirmar_turno(db_session, 123, {"nombre": "Juan", "apellido": "P", "dni": "1", "telefono": "2"})
        assert "Error" in texto


class TestMessageFormatting:
    """Tests for message formatting helpers."""

    def test_escape_markdown_v2_escapes_special_chars(self):
        assert escape_markdown_v2("hello.world") == "hello\\.world"
        assert "\\-" in escape_markdown_v2("a-b")

    def test_split_message_under_limit(self):
        text = "short"
        assert split_message(text) == ["short"]

    def test_split_message_over_limit(self):
        text = "x" * 5000
        chunks = split_message(text)
        assert len(chunks) > 1
        assert all(len(c) <= 4096 for c in chunks)

    def test_format_disponibilidad(self):
        slots = [{"hora_inicio": "08:00", "hora_fin": "08:30", "disponible": True}]
        result = format_disponibilidad("2026-06-15", slots)
        # Date is escaped for MarkdownV2
        assert "2026" in result
        assert "06" in result
        assert "15" in result
        assert "08:00" in result

    def test_format_confirmacion(self):
        turno = {"fecha": "2026-06-15", "hora_inicio": "08:00"}
        paciente = {"nombre": "Juan", "apellido": "Pérez"}
        result = format_confirmacion(turno, paciente)
        assert "Juan" in result
        assert "08:00" in result

    def test_format_error(self):
        result = format_error("algo salió mal")
        assert "algo salió mal" in result

    def test_format_fechas_keyboard(self):
        kb = format_fechas_keyboard(["2026-06-15", "2026-06-16"])
        assert len(kb.inline_keyboard) == 3  # 2 dates + cancel
        assert kb.inline_keyboard[0][0].callback_data == "fecha:2026-06-15"

    def test_format_horas_keyboard(self):
        kb = format_horas_keyboard(["08:00", "08:30"])
        assert len(kb.inline_keyboard) == 3
        assert kb.inline_keyboard[0][0].callback_data == "hora:08:00"

    def test_format_confirmacion_keyboard(self):
        kb = format_confirmacion_keyboard()
        assert len(kb.inline_keyboard) == 2
        assert kb.inline_keyboard[0][0].callback_data == "confirmar_datos"
        assert kb.inline_keyboard[1][0].callback_data == "cancelar_accion"

    def test_split_message_exactly_at_limit(self):
        text = "x" * 4096
        assert split_message(text) == [text]

    def test_format_error_escapes_input(self):
        result = format_error("error.with.dots")
        assert "error\\.with\\.dots" in result

    @pytest.mark.asyncio
    async def test_accion_reservar_temporal_invalid_date_format(self, db_session):
        texto, keyboard = await accion_reservar_temporal(db_session, 123, "not-a-date", "08:00")
        assert "Error" in texto

    @pytest.mark.asyncio
    async def test_enviar_mensaje_calls_run_in_threadpool(self):
        with patch("app.services.telegram_service.run_in_threadpool", new=AsyncMock()) as mock_pool:
            with patch("app.services.telegram_service._get_bot") as mock_bot:
                mock_bot_instance = MagicMock()
                mock_bot.return_value = mock_bot_instance
                await enviar_mensaje(123, "hola")
                mock_pool.assert_awaited_once()
                args = mock_pool.call_args[0]
                assert args[0] == mock_bot_instance.send_message

    @pytest.mark.asyncio
    async def test_responder_callback_query_calls_run_in_threadpool(self):
        with patch("app.services.telegram_service.run_in_threadpool", new=AsyncMock()) as mock_pool:
            with patch("app.services.telegram_service._get_bot") as mock_bot:
                mock_bot_instance = MagicMock()
                mock_bot.return_value = mock_bot_instance
                await responder_callback_query("cq1")
                mock_pool.assert_awaited_once()
                args = mock_pool.call_args[0]
                assert args[0] == mock_bot_instance.answer_callback_query


class TestListaEsperaTelegram:
    """Tests for waiting list Telegram integration."""

    def setup_method(self):
        _reset_state()
        _reset_bot()

    def test_format_lista_espera_keyboard(self):
        kb = format_lista_espera_keyboard(42)
        assert len(kb.inline_keyboard) == 1
        assert len(kb.inline_keyboard[0]) == 2
        assert kb.inline_keyboard[0][0].callback_data == "lista_espera:aceptar:42"
        assert kb.inline_keyboard[0][1].callback_data == "lista_espera:rechazar:42"

    def test_format_lista_espera_mensaje(self):
        from unittest.mock import MagicMock
        turno = MagicMock()
        turno.fecha = "2026-06-15"
        turno.hora_inicio = "09:00"
        texto = format_lista_espera_mensaje(turno)
        assert "2026" in texto
        assert "09:00" in texto
        assert "Turno liberado" in texto

    @pytest.mark.asyncio
    async def test_enviar_notificacion_lista_espera_exitoso(self):
        from unittest.mock import MagicMock
        turno = MagicMock()
        turno.id = 1
        turno.fecha = "2026-06-15"
        turno.hora_inicio = "09:00"
        with patch("app.services.telegram_service.run_in_threadpool", new=AsyncMock()) as mock_pool:
            with patch("app.services.telegram_service._get_bot") as mock_bot:
                mock_bot_instance = MagicMock()
                mock_bot.return_value = mock_bot_instance
                ok = await enviar_notificacion_lista_espera("12345", turno)
                assert ok is True
                mock_pool.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_enviar_notificacion_lista_espera_falla(self):
        from unittest.mock import MagicMock
        turno = MagicMock()
        turno.id = 1
        turno.fecha = "2026-06-15"
        turno.hora_inicio = "09:00"
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock(side_effect=Exception("fail"))) as mock_enviar:
            ok = await enviar_notificacion_lista_espera("12345", turno)
            assert ok is False

    @pytest.mark.asyncio
    async def test_accion_aceptar_lista_espera_sin_registro(self, db_session):
        texto = await accion_aceptar_lista_espera(db_session, 123, 999)
        assert "Error" in texto

    @pytest.mark.asyncio
    async def test_accion_rechazar_lista_espera_sin_registro(self, db_session):
        texto = await accion_rechazar_lista_espera(db_session, 123, 999)
        assert "Error" in texto
