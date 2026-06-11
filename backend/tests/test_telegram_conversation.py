import pytest
from unittest.mock import AsyncMock, patch

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
                await procesar_mensaje(None, update)
                mock_cb.assert_awaited_once()
                mock_send.assert_awaited_once()
                args = mock_send.call_args
                assert "99" in args[0][1]

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
