import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.telegram_service import (
    _get_state,
    _reset_state,
    _reset_bot,
    procesar_mensaje,
)


def _mock_db():
    return None


class TestConversationRouter:
    """Tests for conversational router and state management."""

    def setup_method(self):
        _reset_state()
        _reset_bot()

    @pytest.mark.asyncio
    async def test_start_command_routes_to_show_dates(self):
        """/start should set state to esperando_fecha and show available dates."""
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "chat": {"id": 123},
                "text": "/start",
            },
        }
        with patch("app.services.telegram_service.mostrar_disponibilidad", new=AsyncMock()) as mock_disp:
            mock_disp.return_value = ("msg", None)
            with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                await procesar_mensaje(None, update)
                mock_disp.assert_awaited_once()
                mock_send.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "esperando_fecha"

    @pytest.mark.asyncio
    async def test_quiero_un_turno_routes_to_show_dates(self):
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "chat": {"id": 123},
                "text": "Quiero un turno",
            },
        }
        with patch("app.services.telegram_service.mostrar_disponibilidad", new=AsyncMock()) as mock_disp:
            mock_disp.return_value = ("msg", None)
            with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                await procesar_mensaje(None, update)
                mock_disp.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unrecognized_text_in_idle_returns_help(self):
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "chat": {"id": 123},
                "text": "blabla",
            },
        }
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            await procesar_mensaje(None, update)
            mock_send.assert_awaited_once()
            args = mock_send.call_args
            assert "help" in args[0][1].lower() or "ayuda" in args[0][1].lower() or "comandos" in args[0][1].lower()

    @pytest.mark.asyncio
    async def test_callback_date_routes_to_show_hours(self):
        """callback_data fecha:YYYY-MM-DD should show hours for that date."""
        _get_state(123)["estado"] = "esperando_fecha"
        update = {
            "update_id": 1,
            "callback_query": {
                "id": "cq1",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 1, "chat": {"id": 123}, "text": "msg"},
                "data": "fecha:2026-06-15",
            },
        }
        with patch("app.services.telegram_service.mostrar_disponibilidad", new=AsyncMock()) as mock_disp:
            mock_disp.return_value = ("msg", None)
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()) as mock_cb:
                with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                    await procesar_mensaje(None, update)
                    mock_disp.assert_awaited_once()
                    mock_cb.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "esperando_hora"
        assert state["fecha_seleccionada"] == "2026-06-15"

    @pytest.mark.asyncio
    async def test_callback_time_routes_to_reserve_temporal(self):
        """callback_data hora:HH:MM should create a temporary reservation."""
        _get_state(123)["estado"] = "esperando_hora"
        _get_state(123)["fecha_seleccionada"] = "2026-06-15"
        update = {
            "update_id": 1,
            "callback_query": {
                "id": "cq2",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 1, "chat": {"id": 123}, "text": "msg"},
                "data": "hora:09:00",
            },
        }
        with patch("app.services.telegram_service.accion_reservar_temporal", new=AsyncMock()) as mock_res:
            mock_res.return_value = ("msg", None)
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()) as mock_cb:
                with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                    await procesar_mensaje(None, update)
                    mock_res.assert_awaited_once()
                    mock_cb.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "esperando_datos"

    @pytest.mark.asyncio
    async def test_cancelar_resets_state(self):
        """Cancelar should reset state to idle."""
        _get_state(123)["estado"] = "esperando_hora"
        _get_state(123)["turno_temporal_id"] = 42
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "chat": {"id": 123},
                "text": "Cancelar",
            },
        }
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            await procesar_mensaje(None, update)
            mock_send.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "idle"
        assert state["turno_temporal_id"] is None

    @pytest.mark.asyncio
    async def test_reprogramar_text_routes_to_reschedule(self):
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "chat": {"id": 123},
                "text": "Reprogramar",
            },
        }
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            await procesar_mensaje(None, update)
            mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reminder_confirmar_callback(self):
        update = {
            "update_id": 1,
            "callback_query": {
                "id": "cq3",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 1, "chat": {"id": 123}, "text": "msg"},
                "data": "reminder:confirmar:99",
            },
        }
        with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()) as mock_cb:
            with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                with patch("app.services.telegram_service.confirmar_asistencia_turno", new=AsyncMock()) as mock_confirmar:
                    await procesar_mensaje(None, update)
                    mock_cb.assert_awaited_once()
                    mock_send.assert_awaited_once()
                    mock_confirmar.assert_awaited_once_with(None, 99)
                    args = mock_send.call_args
                    assert "gracias" in args[0][1].lower() or "confirmada" in args[0][1].lower()

    @pytest.mark.asyncio
    async def test_patient_data_collection_transitions_state(self):
        """Sending patient data in esperando_datos state should transition to esperando_confirmacion."""
        _get_state(123)["estado"] = "esperando_datos"
        _get_state(123)["turno_temporal_id"] = 42
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "chat": {"id": 123},
                "text": "Juan, Pérez, 12345678, 5551234",
            },
        }
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            await procesar_mensaje(None, update)
            mock_send.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "esperando_confirmacion"
        assert state["datos_paciente"]["nombre"] == "Juan"
        assert state["datos_paciente"]["dni"] == "12345678"

    @pytest.mark.asyncio
    async def test_callback_cancelar_action(self):
        """callback_data cancelar_accion should reset state."""
        _get_state(123)["estado"] = "esperando_hora"
        _get_state(123)["turno_temporal_id"] = 42
        update = {
            "update_id": 1,
            "callback_query": {
                "id": "cq4",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 1, "chat": {"id": 123}, "text": "msg"},
                "data": "cancelar_accion",
            },
        }
        with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()) as mock_cb:
            with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                await procesar_mensaje(None, update)
                mock_cb.assert_awaited_once()
                mock_send.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "idle"
        assert state["turno_temporal_id"] is None

    # -----------------------------------------------------------------------
    # C-13: Reprogramación Telegram
    # -----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_callback_reprogramar_inicia_flujo(self):
        """callback_data reprogramar:<id> inicia flujo de reprogramación."""
        update = {
            "update_id": 1,
            "callback_query": {
                "id": "cq5",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 1, "chat": {"id": 123}, "text": "msg"},
                "data": "reprogramar:99",
            },
        }
        with patch("app.services.telegram_service.mostrar_disponibilidad", new=AsyncMock()) as mock_disp:
            mock_disp.return_value = ("msg", None)
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()) as mock_cb:
                with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                    await procesar_mensaje(None, update)
                    mock_disp.assert_awaited_once()
                    mock_cb.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "reprogramando_esperando_fecha"
        assert state["turno_a_reprogramar_id"] == 99

    @pytest.mark.asyncio
    async def test_reprogramar_seleccion_fecha_muestra_horas(self):
        """Selección de fecha en reprogramación muestra horarios."""
        _get_state(123)["estado"] = "reprogramando_esperando_fecha"
        _get_state(123)["turno_a_reprogramar_id"] = 99
        update = {
            "update_id": 1,
            "callback_query": {
                "id": "cq6",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 1, "chat": {"id": 123}, "text": "msg"},
                "data": "fecha:2026-06-16",
            },
        }
        with patch("app.services.telegram_service.mostrar_disponibilidad", new=AsyncMock()) as mock_disp:
            mock_disp.return_value = ("msg", None)
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()) as mock_cb:
                with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                    await procesar_mensaje(None, update)
                    mock_disp.assert_awaited_once()
                    mock_cb.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "reprogramando_esperando_hora"
        assert state["nueva_fecha_seleccionada"] == "2026-06-16"

    @pytest.mark.asyncio
    async def test_reprogramar_seleccion_hora_exitosa(self):
        """Selección de horario exitoso llama reprogramar_turno y envía confirmación."""
        _get_state(123)["estado"] = "reprogramando_esperando_hora"
        _get_state(123)["turno_a_reprogramar_id"] = 99
        _get_state(123)["nueva_fecha_seleccionada"] = "2026-06-16"
        update = {
            "update_id": 1,
            "callback_query": {
                "id": "cq7",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 1, "chat": {"id": 123}, "text": "msg"},
                "data": "hora:10:00",
            },
        }
        mock_turno = MagicMock()
        mock_turno.fecha = "2026-06-16"
        mock_turno.hora_inicio = "10:00"
        with patch("app.services.telegram_service.reprogramar_turno", new=AsyncMock()) as mock_repr:
            mock_repr.return_value = mock_turno
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()) as mock_cb:
                with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                    await procesar_mensaje(None, update)
                    mock_repr.assert_awaited_once()
                    mock_cb.assert_awaited_once()
                    mock_send.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "idle"

    @pytest.mark.asyncio
    async def test_reprogramar_seleccion_hora_no_disponible(self):
        """Selección de horario no disponible notifica error y permite reintentar."""
        from app.exceptions import TurnoNoDisponibleError
        _get_state(123)["estado"] = "reprogramando_esperando_hora"
        _get_state(123)["turno_a_reprogramar_id"] = 99
        _get_state(123)["nueva_fecha_seleccionada"] = "2026-06-16"
        update = {
            "update_id": 1,
            "callback_query": {
                "id": "cq8",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 1, "chat": {"id": 123}, "text": "msg"},
                "data": "hora:10:00",
            },
        }
        with patch("app.services.telegram_service.reprogramar_turno", new=AsyncMock()) as mock_repr:
            mock_repr.side_effect = TurnoNoDisponibleError("Slot no disponible")
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()) as mock_cb:
                with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                    await procesar_mensaje(None, update)
                    mock_repr.assert_awaited_once()
                    mock_cb.assert_awaited_once()
                    mock_send.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "reprogramando_esperando_fecha"

    @pytest.mark.asyncio
    async def test_reprogramar_cancelar_limpia_estado(self):
        """Cancelar flujo de reprogramación limpia estado."""
        _get_state(123)["estado"] = "reprogramando_esperando_fecha"
        _get_state(123)["turno_a_reprogramar_id"] = 99
        update = {
            "update_id": 1,
            "callback_query": {
                "id": "cq9",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 1, "chat": {"id": 123}, "text": "msg"},
                "data": "cancelar_accion",
            },
        }
        with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()) as mock_cb:
            with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                await procesar_mensaje(None, update)
                mock_cb.assert_awaited_once()
                mock_send.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "idle"
        assert state["turno_a_reprogramar_id"] is None
        assert state["nueva_fecha_seleccionada"] is None

    @pytest.mark.asyncio
    async def test_reprogramar_turno_ya_cancelado_limpia_estado(self):
        """Reprogramación de turno cancelado notifica y limpia estado."""
        from app.exceptions import TurnoYaCanceladoError
        _get_state(123)["estado"] = "reprogramando_esperando_hora"
        _get_state(123)["turno_a_reprogramar_id"] = 99
        _get_state(123)["nueva_fecha_seleccionada"] = "2026-06-16"
        update = {
            "update_id": 1,
            "callback_query": {
                "id": "cq10",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 1, "chat": {"id": 123}, "text": "msg"},
                "data": "hora:10:00",
            },
        }
        with patch("app.services.telegram_service.reprogramar_turno", new=AsyncMock()) as mock_repr:
            mock_repr.side_effect = TurnoYaCanceladoError("Turno cancelado")
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()) as mock_cb:
                with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                    await procesar_mensaje(None, update)
                    mock_repr.assert_awaited_once()
                    mock_cb.assert_awaited_once()
                    mock_send.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "idle"
        assert state["turno_a_reprogramar_id"] is None
        assert state["nueva_fecha_seleccionada"] is None

    @pytest.mark.asyncio
    async def test_reprogramar_error_inesperado_limpia_estado(self):
        """Error inesperado durante reprogramación notifica y limpia estado."""
        _get_state(123)["estado"] = "reprogramando_esperando_hora"
        _get_state(123)["turno_a_reprogramar_id"] = 99
        _get_state(123)["nueva_fecha_seleccionada"] = "2026-06-16"
        update = {
            "update_id": 1,
            "callback_query": {
                "id": "cq11",
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 1, "chat": {"id": 123}, "text": "msg"},
                "data": "hora:10:00",
            },
        }
        with patch("app.services.telegram_service.reprogramar_turno", new=AsyncMock()) as mock_repr:
            mock_repr.side_effect = RuntimeError("Calendar API down")
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()) as mock_cb:
                with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
                    await procesar_mensaje(None, update)
                    mock_repr.assert_awaited_once()
                    mock_cb.assert_awaited_once()
                    mock_send.assert_awaited_once()
        state = _get_state(123)
        assert state["estado"] == "idle"
        assert state["turno_a_reprogramar_id"] is None
        assert state["nueva_fecha_seleccionada"] is None
