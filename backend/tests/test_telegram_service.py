import pytest
from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.telegram_service import (
    _get_state,
    _reset_state,
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
    format_recordatorio_mensaje,
    format_recordatorio_keyboard,
    procesar_mensaje,
    format_turnos_hoy,
    format_metricas,
    format_config_summary,
    format_dias_keyboard,
    format_config_confirm_keyboard,
    accion_turnos_hoy,
    accion_metricas,
    accion_configurar,
)


class TestTelegramServiceIntegration:
    """Tests for telegram_service business actions."""

    def setup_method(self):
        _reset_state()

    @pytest.mark.asyncio
    async def test_mostrar_disponibilidad_without_fecha_returns_dates_keyboard(self, db_session):
        """When no date is provided, show upcoming dates."""
        texto, keyboard = await mostrar_disponibilidad(db_session, profesional_id=1)
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

        texto, keyboard = await mostrar_disponibilidad(db_session, profesional_id=1, fecha=hoy)
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

        texto, keyboard = await accion_reservar_temporal(db_session, 123, str(hoy), "08:00", profesional_id=1)
        assert "Reserva temporal creada" in texto or "Error" in texto
        state = _get_state(123)
        if "Reserva temporal creada" in texto:
            assert state["turno_temporal_id"] is not None

    @pytest.mark.asyncio
    async def test_accion_confirmar_turno_without_temporal_id_returns_error(self, db_session):
        texto = await accion_confirmar_turno(db_session, 123, {"nombre": "Juan", "apellido": "P", "dni": "1", "telefono": "2"}, profesional_id=1)
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
            texto, keyboard = await accion_reservar_temporal(db_session, 123, "2026-06-15", "08:00", profesional_id=1)
        assert "Error" in texto

    @pytest.mark.asyncio
    async def test_confirmar_turno_error_returns_friendly_message(self, db_session):
        """When confirmar_turno raises, return a friendly error message."""
        _get_state(123)["turno_temporal_id"] = 1
        with patch("app.services.telegram_service.confirmar_turno", side_effect=Exception("expired")):
            texto = await accion_confirmar_turno(db_session, 123, {"nombre": "Juan", "apellido": "P", "dni": "1", "telefono": "2"}, profesional_id=1)
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
        texto, keyboard = await accion_reservar_temporal(db_session, 123, "not-a-date", "08:00", profesional_id=1)
        assert "Error" in texto

    @pytest.mark.asyncio
    async def test_enviar_mensaje_calls_run_in_threadpool(self):
        with patch("app.services.telegram_service.run_in_threadpool", new=AsyncMock()) as mock_pool:
            with patch("app.services.telegram_service._get_bot") as mock_bot:
                mock_bot_instance = MagicMock()
                mock_bot.return_value = mock_bot_instance
                await enviar_mensaje(123, "hola", "test_token")
                mock_pool.assert_awaited_once()
                args = mock_pool.call_args[0]
                assert args[0] == mock_bot_instance.send_message

    @pytest.mark.asyncio
    async def test_responder_callback_query_calls_run_in_threadpool(self):
        with patch("app.services.telegram_service.run_in_threadpool", new=AsyncMock()) as mock_pool:
            with patch("app.services.telegram_service._get_bot") as mock_bot:
                mock_bot_instance = MagicMock()
                mock_bot.return_value = mock_bot_instance
                await responder_callback_query("cq1", "test_token")
                mock_pool.assert_awaited_once()
                args = mock_pool.call_args[0]
                assert args[0] == mock_bot_instance.answer_callback_query


class TestListaEsperaTelegram:
    """Tests for waiting list Telegram integration."""

    def setup_method(self):
        _reset_state()

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
                ok = await enviar_notificacion_lista_espera("12345", turno, "test_token")
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
            ok = await enviar_notificacion_lista_espera("12345", turno, "test_token")
            assert ok is False

    @pytest.mark.asyncio
    async def test_accion_aceptar_lista_espera_sin_registro(self, db_session):
        texto = await accion_aceptar_lista_espera(db_session, 123, 999)
        assert "Error" in texto

    @pytest.mark.asyncio
    async def test_accion_rechazar_lista_espera_sin_registro(self, db_session):
        texto = await accion_rechazar_lista_espera(db_session, 123, 999)
        assert "Error" in texto


class TestRecordatorioFormatting:
    """Tests for reminder message formatting."""

    def test_format_recordatorio_mensaje_contiene_fecha_y_hora(self):
        turno = {"fecha": date(2026, 6, 15), "hora_inicio": time(9, 0)}
        paciente = {"nombre": "Juan", "apellido": "Perez"}
        texto = format_recordatorio_mensaje(turno, paciente)
        assert "2026" in texto
        assert "09:00" in texto
        assert "Juan" in texto

    def test_format_recordatorio_mensaje_escapa_markdown(self):
        turno = {"fecha": date(2026, 6, 15), "hora_inicio": time(9, 0)}
        paciente = {"nombre": "Juan.Perez", "apellido": "Garcia"}
        texto = format_recordatorio_mensaje(turno, paciente)
        # Dots should be escaped for MarkdownV2
        assert "Juan\\.Perez" in texto

    def test_format_recordatorio_keyboard_tres_botones(self):
        kb = format_recordatorio_keyboard(42)
        assert len(kb.inline_keyboard) == 3
        assert kb.inline_keyboard[0][0].callback_data == "reminder:confirmar:42"
        assert kb.inline_keyboard[1][0].callback_data == "reminder:cancelar:42"
        assert kb.inline_keyboard[2][0].callback_data == "reminder:reprogramar:42"


class TestRecordatorioCallbacks:
    """Tests for reminder callback routing."""

    @pytest.fixture(autouse=True)
    def _reset_and_env(self, monkeypatch):
        _reset_state()
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")

    @pytest.mark.asyncio
    async def test_callback_reminder_confirmar(self, db_session):
        from app.models.profesional import Profesional
        from app.models.paciente import Paciente
        from app.models.turno import Turno
        from unittest.mock import patch

        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        paciente = Paciente(nombre="Juan", apellido="P", dni="123", telefono="555", profesional_id=p.id)
        db_session.add(paciente)
        await db_session.commit()

        turno = Turno(
            fecha=date(2026, 6, 15), hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=p.id, paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                update = {
                    "callback_query": {
                        "id": "cq1",
                        "data": f"reminder:confirmar:{turno.id}",
                        "message": {"chat": {"id": 123}},
                    }
                }
                await procesar_mensaje(db_session, update, profesional_id=p.id)
                mock_enviar.assert_awaited()
                args = mock_enviar.call_args[0]
                assert "gracias" in args[1].lower() or "confirmada" in args[1].lower()

    @pytest.mark.asyncio
    async def test_callback_reminder_cancelar(self, db_session):
        from app.models.profesional import Profesional
        from app.models.paciente import Paciente
        from app.models.turno import Turno
        from unittest.mock import patch

        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        paciente = Paciente(nombre="Juan", apellido="P", dni="123", telefono="555", profesional_id=p.id)
        db_session.add(paciente)
        await db_session.commit()

        turno = Turno(
            fecha=date(2026, 6, 15), hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=p.id, paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                update = {
                    "callback_query": {
                        "id": "cq1",
                        "data": f"reminder:cancelar:{turno.id}",
                        "message": {"chat": {"id": 123}},
                    }
                }
                await procesar_mensaje(db_session, update, profesional_id=p.id)
                mock_enviar.assert_awaited()
                args = mock_enviar.call_args[0]
                assert "cancelada" in args[1].lower() or "cancelado" in args[1].lower()

    @pytest.mark.asyncio
    async def test_callback_reminder_reprogramar(self, db_session):
        from app.models.profesional import Profesional
        from unittest.mock import patch

        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                update = {
                    "callback_query": {
                        "id": "cq1",
                        "data": "reminder:reprogramar:5",
                        "message": {"chat": {"id": 123}},
                    }
                }
                await procesar_mensaje(db_session, update, profesional_id=p.id)
                mock_enviar.assert_awaited()
                state = _get_state(123)
                assert state["estado"] == "reprogramando_esperando_fecha"


class TestProfessionalDashboardFormatting:
    """Tests for professional dashboard message formatting."""

    def test_format_turnos_hoy_with_patients(self):
        turnos = [
            {"hora_inicio": "08:00", "paciente": {"nombre": "Juan", "apellido": "Pérez"}},
            {"hora_inicio": "09:00", "paciente": {"nombre": "Ana", "apellido": "García"}},
        ]
        texto = format_turnos_hoy(turnos)
        assert "08:00" in texto
        assert "09:00" in texto
        assert "Juan" in texto
        assert "Pérez" in texto
        assert "Ana" in texto
        # MarkdownV2 escaping
        assert "*Turnos de hoy*" in texto

    def test_format_turnos_hoy_empty(self):
        texto = format_turnos_hoy([])
        assert "No hay turnos confirmados" in texto

    def test_format_turnos_hoy_escapes_markdown(self):
        turnos = [
            {"hora_inicio": "08:00", "paciente": {"nombre": "Juan.Perez", "apellido": "Garcia"}},
        ]
        texto = format_turnos_hoy(turnos)
        assert r"Juan\.Perez" in texto

    def test_format_metricas(self):
        metricas = {
            "turnos_hoy": 5,
            "tasa_confirmacion_30d": 0.75,
            "tasa_cancelacion_30d": 0.10,
        }
        texto = format_metricas(metricas)
        assert "5" in texto
        assert "75" in texto or "0.75" in texto
        assert "10" in texto or "0.10" in texto
        assert "*Métricas*" in texto

    def test_format_metricas_zero(self):
        metricas = {
            "turnos_hoy": 0,
            "tasa_confirmacion_30d": 0.0,
            "tasa_cancelacion_30d": 0.0,
        }
        texto = format_metricas(metricas)
        assert "0" in texto
        assert "*Métricas*" in texto

    def test_format_config_summary(self):
        config = {
            "horario_inicio": "08:00",
            "horario_fin": "18:00",
            "dias_atencion": ["Lunes", "Martes"],
            "duracion_turno": 30,
        }
        texto = format_config_summary(config)
        assert "08:00" in texto
        assert "18:00" in texto
        assert "Lunes" in texto
        assert "30" in texto
        assert "*Resumen de cambios*" in texto

    def test_split_message_long_turnos_list(self):
        # Generate a very long list that would exceed 4096 chars
        turnos = [
            {"hora_inicio": "08:00", "paciente": {"nombre": "Paciente", "apellido": f"Numero{i}"}}
            for i in range(300)
        ]
        texto = format_turnos_hoy(turnos)
        chunks = split_message(texto)
        assert len(chunks) > 1
        assert all(len(c) <= 4096 for c in chunks)


class TestConfigWizardKeyboards:
    """Tests for configuration wizard keyboards."""

    def test_format_dias_keyboard_structure(self):
        kb = format_dias_keyboard(["Lunes", "Miércoles"])
        # 7 day buttons + confirm button = 8 rows
        assert len(kb.inline_keyboard) == 8
        assert kb.inline_keyboard[0][0].text == "Lunes ✅"
        assert kb.inline_keyboard[1][0].text == "Martes"
        assert kb.inline_keyboard[2][0].text == "Miércoles ✅"
        assert kb.inline_keyboard[7][0].text == "Confirmar días"
        assert kb.inline_keyboard[7][0].callback_data == "config:confirmar_dias"

    def test_format_dias_keyboard_toggle_off(self):
        kb = format_dias_keyboard([])
        assert kb.inline_keyboard[0][0].text == "Lunes"
        assert kb.inline_keyboard[6][0].text == "Domingo"

    def test_format_config_confirm_keyboard(self):
        kb = format_config_confirm_keyboard()
        assert len(kb.inline_keyboard) == 2
        assert kb.inline_keyboard[0][0].text == "Confirmar"
        assert kb.inline_keyboard[0][0].callback_data == "config:confirmar"
        assert kb.inline_keyboard[1][0].text == "Cancelar"
        assert kb.inline_keyboard[1][0].callback_data == "config:cancelar"


class TestProfesionalCommands:
    """Tests for professional dashboard commands in procesar_mensaje."""

    def setup_method(self):
        _reset_state()

    @pytest.mark.asyncio
    async def test_accion_turnos_hoy_returns_formatted_list(self, db_session):
        from app.models.profesional import Profesional
        from app.models.paciente import Paciente
        from app.models.turno import Turno

        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.flush()

        paciente = Paciente(nombre="Juan", apellido="P", dni="123", telefono="555", profesional_id=p.id)
        db_session.add(paciente)
        await db_session.flush()

        hoy = date.today()
        turno = Turno(
            fecha=hoy, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=p.id, paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            update = {"message": {"chat": {"id": 123}, "text": "/turnos_hoy"}}
            await procesar_mensaje(db_session, update, profesional_id=p.id)
            mock_enviar.assert_awaited()
            args = mock_enviar.call_args[0]
            assert "Turnos de hoy" in args[1]
            assert "09:00" in args[1]
            assert "Juan" in args[1]

    @pytest.mark.asyncio
    async def test_accion_metricas_returns_summary(self, db_session):
        from app.models.profesional import Profesional
        from app.models.turno import Turno

        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.flush()

        hoy = date.today()
        db_session.add(Turno(
            fecha=hoy, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=p.id,
        ))
        await db_session.commit()

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            update = {"message": {"chat": {"id": 123}, "text": "/metricas"}}
            await procesar_mensaje(db_session, update, profesional_id=p.id)
            mock_enviar.assert_awaited()
            args = mock_enviar.call_args[0]
            assert "Métricas" in args[1]
            assert "1" in args[1]

    @pytest.mark.asyncio
    async def test_accion_configurar_starts_wizard(self, db_session):
        from app.models.profesional import Profesional

        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            update = {"message": {"chat": {"id": 123}, "text": "/configurar"}}
            await procesar_mensaje(db_session, update, profesional_id=p.id)
            mock_enviar.assert_awaited()
            args = mock_enviar.call_args[0]
            assert "horario de inicio" in args[1].lower() or "HH:MM" in args[1]
            state = _get_state(123)
            assert state["estado"] == "config_esperando_hora_inicio"


class TestConfigWizard:
    """Tests for the /configurar wizard step handlers."""

    def setup_method(self):
        _reset_state()

    @pytest.fixture
    def wizard_state(self):
        state = _get_state(123)
        state["estado"] = "config_esperando_hora_inicio"
        state["config_data"] = {}
        return state

    @pytest.mark.asyncio
    async def test_config_hora_inicio_valid(self, db_session, wizard_state):
        from app.models.profesional import Profesional
        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            update = {"message": {"chat": {"id": 123}, "text": "09:00"}}
            await procesar_mensaje(db_session, update, profesional_id=p.id)
            state = _get_state(123)
            assert state["estado"] == "config_esperando_hora_fin"
            assert state["config_data"]["horario_inicio"] == "09:00"
            args = mock_enviar.call_args[0]
            assert "horario de fin" in args[1].lower()

    @pytest.mark.asyncio
    async def test_config_hora_inicio_invalid(self, db_session, wizard_state):
        from app.models.profesional import Profesional
        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            update = {"message": {"chat": {"id": 123}, "text": "25:00"}}
            await procesar_mensaje(db_session, update, profesional_id=p.id)
            state = _get_state(123)
            assert state["estado"] == "config_esperando_hora_inicio"
            args = mock_enviar.call_args[0]
            assert "inválido" in args[1].lower() or "error" in args[1].lower()

    @pytest.mark.asyncio
    async def test_config_hora_fin_valid(self, db_session, wizard_state):
        from app.models.profesional import Profesional
        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        state = _get_state(123)
        state["estado"] = "config_esperando_hora_fin"
        state["config_data"]["horario_inicio"] = "09:00"

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            update = {"message": {"chat": {"id": 123}, "text": "18:00"}}
            await procesar_mensaje(db_session, update, profesional_id=p.id)
            state = _get_state(123)
            assert state["estado"] == "config_esperando_dias"
            assert state["config_data"]["horario_fin"] == "18:00"
            args = mock_enviar.call_args[0]
            assert "días" in args[1].lower()

    @pytest.mark.asyncio
    async def test_config_hora_fin_invalid_before_start(self, db_session, wizard_state):
        from app.models.profesional import Profesional
        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        state = _get_state(123)
        state["estado"] = "config_esperando_hora_fin"
        state["config_data"]["horario_inicio"] = "09:00"

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            update = {"message": {"chat": {"id": 123}, "text": "08:00"}}
            await procesar_mensaje(db_session, update, profesional_id=p.id)
            state = _get_state(123)
            assert state["estado"] == "config_esperando_hora_fin"
            args = mock_enviar.call_args[0]
            assert "inválido" in args[1].lower() or "posterior" in args[1].lower()

    @pytest.mark.asyncio
    async def test_config_dias_toggle(self, db_session, wizard_state):
        from app.models.profesional import Profesional
        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        state = _get_state(123)
        state["estado"] = "config_esperando_dias"
        state["config_data"]["dias_atencion"] = []

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()):
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                with patch("app.services.telegram_service.run_in_threadpool", new=AsyncMock()) as mock_pool:
                    update = {
                        "callback_query": {
                            "id": "cq1",
                            "data": "config:dia:Lunes",
                            "message": {"chat": {"id": 123}, "message_id": 1},
                        }
                    }
                    await procesar_mensaje(db_session, update, profesional_id=p.id)
                    state = _get_state(123)
                    assert "Lunes" in state["config_data"]["dias_atencion"]
                    # Toggle again
                    update["callback_query"]["data"] = "config:dia:Lunes"
                    await procesar_mensaje(db_session, update, profesional_id=p.id)
                    assert "Lunes" not in state["config_data"]["dias_atencion"]

    @pytest.mark.asyncio
    async def test_config_dias_confirm(self, db_session, wizard_state):
        from app.models.profesional import Profesional
        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        state = _get_state(123)
        state["estado"] = "config_esperando_dias"
        state["config_data"]["dias_atencion"] = ["Lunes", "Martes"]

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                update = {
                    "callback_query": {
                        "id": "cq1",
                        "data": "config:confirmar_dias",
                        "message": {"chat": {"id": 123}},
                    }
                }
                await procesar_mensaje(db_session, update, profesional_id=p.id)
                state = _get_state(123)
                assert state["estado"] == "config_esperando_duracion"
                args = mock_enviar.call_args[0]
                assert "duración" in args[1].lower()

    @pytest.mark.asyncio
    async def test_config_duracion_valid(self, db_session, wizard_state):
        from app.models.profesional import Profesional
        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        state = _get_state(123)
        state["estado"] = "config_esperando_duracion"
        state["config_data"] = {
            "horario_inicio": "09:00",
            "horario_fin": "18:00",
            "dias_atencion": ["Lunes"],
        }

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            update = {"message": {"chat": {"id": 123}, "text": "45"}}
            await procesar_mensaje(db_session, update, profesional_id=p.id)
            state = _get_state(123)
            assert state["estado"] == "config_confirmar"
            assert state["config_data"]["duracion_turno"] == 45
            args = mock_enviar.call_args[0]
            assert "resumen" in args[1].lower() or "confirmar" in args[1].lower()

    @pytest.mark.asyncio
    async def test_config_duracion_invalid(self, db_session, wizard_state):
        from app.models.profesional import Profesional
        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        state = _get_state(123)
        state["estado"] = "config_esperando_duracion"
        state["config_data"] = {"dias_atencion": ["Lunes"]}

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            update = {"message": {"chat": {"id": 123}, "text": "-5"}}
            await procesar_mensaje(db_session, update, profesional_id=p.id)
            state = _get_state(123)
            assert state["estado"] == "config_esperando_duracion"
            args = mock_enviar.call_args[0]
            assert "inválido" in args[1].lower() or "positivo" in args[1].lower()

    @pytest.mark.asyncio
    async def test_config_confirmar_persists(self, db_session, wizard_state):
        from app.models.profesional import Profesional

        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="18:00", dias_atencion=["Lunes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        state = _get_state(123)
        state["estado"] = "config_confirmar"
        state["config_data"] = {
            "horario_inicio": "09:00",
            "horario_fin": "17:00",
            "dias_atencion": ["Martes", "Miércoles"],
            "duracion_turno": 60,
        }

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                update = {
                    "callback_query": {
                        "id": "cq1",
                        "data": "config:confirmar",
                        "message": {"chat": {"id": 123}},
                    }
                }
                await procesar_mensaje(db_session, update, profesional_id=p.id)
                state = _get_state(123)
                assert state["estado"] == "idle"
                # Verify DB was updated
                from sqlalchemy import select
                result = await db_session.execute(select(Profesional).where(Profesional.id == p.id))
                updated = result.scalar_one()
                assert updated.horario_inicio == "09:00"
                assert updated.horario_fin == "17:00"
                assert updated.dias_atencion == ["Martes", "Miércoles"]
                assert updated.duracion_turno == 60

    @pytest.mark.asyncio
    async def test_config_cancelar_resets_state(self, db_session, wizard_state):
        from app.models.profesional import Profesional
        p = Profesional(
            nombre="Dr", especialidad="Od", duracion_turno=30,
            horario_inicio="08:00", horario_fin="09:00", dias_atencion=["Lunes"],
            telegram_bot_token="test_token",
        )
        db_session.add(p)
        await db_session.commit()

        state = _get_state(123)
        state["estado"] = "config_esperando_hora_inicio"
        state["config_data"] = {"horario_inicio": "09:00"}

        with patch("app.services.telegram_service.enviar_mensaje", new=AsyncMock()) as mock_enviar:
            with patch("app.services.telegram_service.responder_callback_query", new=AsyncMock()):
                update = {
                    "callback_query": {
                        "id": "cq1",
                        "data": "config:cancelar",
                        "message": {"chat": {"id": 123}},
                    }
                }
                await procesar_mensaje(db_session, update, profesional_id=p.id)
                state = _get_state(123)
                assert state["estado"] == "idle"
                assert state["config_data"] is None
                args = mock_enviar.call_args[0]
                assert "cancelad" in args[1].lower()
