import pytest
from datetime import date, time
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.telegram_service import (
    _get_state,
    _reset_state,
    _reset_bot,
    procesar_mensaje,
)
from app.models.profesional import Profesional
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal


class TestTelegramE2E:
    """End-to-end tests for the Telegram conversation flow."""

    @pytest.fixture(autouse=True)
    def _reset_and_env(self, monkeypatch):
        _reset_state()
        _reset_bot()
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")

    @pytest.mark.asyncio
    async def test_e2e_flujo_completo_reserva(self, db_session):
        """Full flow: /start -> fecha -> hora -> datos -> confirmar."""
        # Setup profesional
        db_session.add(Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        ))
        await db_session.commit()

        hoy = date.today()
        while hoy.strftime("%A") not in {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}:
            hoy = date.fromordinal(hoy.toordinal() + 1)
        fecha_str = str(hoy)

        chat_id = 999

        # Step 1: /start
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            await procesar_mensaje(db_session, {
                "update_id": 1,
                "message": {"message_id": 1, "chat": {"id": chat_id}, "text": "/start"},
            })
            assert mock_send.call_count == 1
        state = _get_state(chat_id)
        assert state["estado"] == "esperando_fecha"

        # Step 2: select date
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                await procesar_mensaje(db_session, {
                    "update_id": 2,
                    "callback_query": {
                        "id": "cq1",
                        "from": {"id": chat_id, "is_bot": False, "first_name": "Test"},
                        "message": {"message_id": 2, "chat": {"id": chat_id}, "text": "msg"},
                        "data": f"fecha:{fecha_str}",
                    },
                })
            assert mock_send.call_count == 1
        state = _get_state(chat_id)
        assert state["estado"] == "esperando_hora"
        assert state["fecha_seleccionada"] == fecha_str

        # Step 3: select time
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                await procesar_mensaje(db_session, {
                    "update_id": 3,
                    "callback_query": {
                        "id": "cq2",
                        "from": {"id": chat_id, "is_bot": False, "first_name": "Test"},
                        "message": {"message_id": 3, "chat": {"id": chat_id}, "text": "msg"},
                        "data": "hora:08:00",
                    },
                })
            assert mock_send.call_count == 1
        state = _get_state(chat_id)
        assert state["estado"] == "esperando_datos"
        assert state["turno_temporal_id"] is not None

        # Step 4: provide patient data
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            await procesar_mensaje(db_session, {
                "update_id": 4,
                "message": {"message_id": 4, "chat": {"id": chat_id}, "text": "Juan, Pérez, 12345678, 5551234"},
            })
            assert mock_send.call_count == 1
        state = _get_state(chat_id)
        assert state["estado"] == "esperando_confirmacion"
        assert state["datos_paciente"]["nombre"] == "Juan"

        # Step 5: confirm
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                await procesar_mensaje(db_session, {
                    "update_id": 5,
                    "callback_query": {
                        "id": "cq3",
                        "from": {"id": chat_id, "is_bot": False, "first_name": "Test"},
                        "message": {"message_id": 5, "chat": {"id": chat_id}, "text": "msg"},
                        "data": "confirmar_datos",
                    },
                })
            assert mock_send.call_count == 1
        state = _get_state(chat_id)
        assert state["estado"] == "idle"
        assert state["turno_temporal_id"] is None

        # Verify turno is CONFIRMADO in DB
        result = await db_session.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(Turno).where(Turno.estado == "CONFIRMADO")
        )
        turnos = result.scalars().all()
        assert len(turnos) == 1

    @pytest.mark.asyncio
    async def test_e2e_cancelar_en_medio_del_flujo(self, db_session):
        """Cancelar in the middle of the flow should reset state and delete temporal."""
        db_session.add(Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        ))
        await db_session.commit()

        hoy = date.today()
        while hoy.strftime("%A") not in {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}:
            hoy = date.fromordinal(hoy.toordinal() + 1)

        chat_id = 888

        # Start and select date/time
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()):
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                await procesar_mensaje(db_session, {
                    "update_id": 1,
                    "message": {"message_id": 1, "chat": {"id": chat_id}, "text": "/start"},
                })
                await procesar_mensaje(db_session, {
                    "update_id": 2,
                    "callback_query": {
                        "id": "cq1",
                        "from": {"id": chat_id, "is_bot": False, "first_name": "Test"},
                        "message": {"message_id": 2, "chat": {"id": chat_id}, "text": "msg"},
                        "data": f"fecha:{hoy}",
                    },
                })
                await procesar_mensaje(db_session, {
                    "update_id": 3,
                    "callback_query": {
                        "id": "cq2",
                        "from": {"id": chat_id, "is_bot": False, "first_name": "Test"},
                        "message": {"message_id": 3, "chat": {"id": chat_id}, "text": "msg"},
                        "data": "hora:08:00",
                    },
                })

        state = _get_state(chat_id)
        turno_id = state["turno_temporal_id"]
        assert turno_id is not None

        # Cancel
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            await procesar_mensaje(db_session, {
                "update_id": 4,
                "message": {"message_id": 4, "chat": {"id": chat_id}, "text": "Cancelar"},
            })
        state = _get_state(chat_id)
        assert state["estado"] == "idle"
        assert state["turno_temporal_id"] is None

    @pytest.mark.asyncio
    async def test_e2e_turno_no_disponible_durante_reserva(self, db_session):
        """When the slot is no longer available, show a friendly error."""
        db_session.add(Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        ))
        await db_session.commit()

        hoy = date.today()
        while hoy.strftime("%A") not in {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}:
            hoy = date.fromordinal(hoy.toordinal() + 1)

        chat_id = 777

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                await procesar_mensaje(db_session, {
                    "update_id": 1,
                    "message": {"message_id": 1, "chat": {"id": chat_id}, "text": "/start"},
                })
                await procesar_mensaje(db_session, {
                    "update_id": 2,
                    "callback_query": {
                        "id": "cq1",
                        "from": {"id": chat_id, "is_bot": False, "first_name": "Test"},
                        "message": {"message_id": 2, "chat": {"id": chat_id}, "text": "msg"},
                        "data": f"fecha:{hoy}",
                    },
                })
                # Try to reserve a non-existent slot
                await procesar_mensaje(db_session, {
                    "update_id": 3,
                    "callback_query": {
                        "id": "cq2",
                        "from": {"id": chat_id, "is_bot": False, "first_name": "Test"},
                        "message": {"message_id": 3, "chat": {"id": chat_id}, "text": "msg"},
                        "data": "hora:99:99",
                    },
                })
            # Should have sent an error message
            calls = mock_send.call_args_list
            assert any("Error" in str(c) for c in calls)

    @pytest.mark.asyncio
    async def test_e2e_mensaje_no_reconocido_idle(self, db_session):
        """Unrecognized message in idle state should show help."""
        chat_id = 666
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            await procesar_mensaje(db_session, {
                "update_id": 1,
                "message": {"message_id": 1, "chat": {"id": chat_id}, "text": "xyz123"},
            })
            args = mock_send.call_args
            assert "Comandos disponibles" in args[0][1] or "help" in args[0][1].lower()

    @pytest.mark.asyncio
    async def test_e2e_botones_inline_callback_query(self, db_session):
        """Inline button presses should be parsed and routed correctly."""
        db_session.add(Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        ))
        await db_session.commit()

        hoy = date.today()
        while hoy.strftime("%A") not in {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}:
            hoy = date.fromordinal(hoy.toordinal() + 1)

        chat_id = 555
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()) as mock_cb:
                await procesar_mensaje(db_session, {
                    "update_id": 1,
                    "callback_query": {
                        "id": "cq1",
                        "from": {"id": chat_id, "is_bot": False, "first_name": "Test"},
                        "message": {"message_id": 1, "chat": {"id": chat_id}, "text": "msg"},
                        "data": f"fecha:{hoy}",
                    },
                })
                mock_cb.assert_awaited_once()
                mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_e2e_recordatorio_confirmar_asistencia(self, db_session):
        """Paciente presiona Confirmar asistencia desde recordatorio."""
        from app.models.paciente import Paciente
        from app.models.turno import Turno

        db_session.add(Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        ))
        await db_session.commit()

        paciente = Paciente(nombre="Juan", apellido="P", dni="123", telefono="555", telegram_chat_id="12345")
        db_session.add(paciente)
        await db_session.commit()

        turno = Turno(
            fecha=date(2026, 6, 15), hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=1, paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()

        chat_id = 444
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                await procesar_mensaje(db_session, {
                    "update_id": 1,
                    "callback_query": {
                        "id": "cq1",
                        "from": {"id": chat_id, "is_bot": False, "first_name": "Test"},
                        "message": {"message_id": 1, "chat": {"id": chat_id}, "text": "msg"},
                        "data": f"reminder:confirmar:{turno.id}",
                    },
                })
        args = mock_send.call_args[0]
        assert "gracias" in args[1].lower() or "confirmada" in args[1].lower()

    @pytest.mark.asyncio
    async def test_e2e_recordatorio_cancelar(self, db_session):
        """Paciente presiona Cancelar desde recordatorio."""
        from app.models.paciente import Paciente
        from app.models.turno import Turno
        from sqlalchemy import select

        db_session.add(Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        ))
        await db_session.commit()

        paciente = Paciente(nombre="Juan", apellido="P", dni="124", telefono="555", telegram_chat_id="12345")
        db_session.add(paciente)
        await db_session.commit()

        turno = Turno(
            fecha=date(2026, 6, 15), hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=1, paciente_id=paciente.id, google_event_id="event_123",
        )
        db_session.add(turno)
        await db_session.commit()

        chat_id = 333
        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_send:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
                    mock_service = MagicMock()
                    mock_calendar_cls.return_value = mock_service
                    await procesar_mensaje(db_session, {
                        "update_id": 1,
                        "callback_query": {
                            "id": "cq1",
                            "from": {"id": chat_id, "is_bot": False, "first_name": "Test"},
                            "message": {"message_id": 1, "chat": {"id": chat_id}, "text": "msg"},
                            "data": f"reminder:cancelar:{turno.id}",
                        },
                    })

        result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
        turno_db = result.scalar_one()
        assert turno_db.estado == "CANCELADO"
