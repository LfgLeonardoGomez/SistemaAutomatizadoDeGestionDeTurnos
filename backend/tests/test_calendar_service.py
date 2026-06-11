import pytest
from datetime import date, time
from unittest.mock import patch, MagicMock

from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.turno import Turno
from app.services.calendar_service import CalendarService


class TestCalendarService:
    @pytest.fixture
    def mock_service(self):
        with patch("app.services.calendar_service.build") as mock_build, \
             patch("app.services.calendar_service.Credentials.from_service_account_info") as mock_creds:
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            mock_creds.return_value = MagicMock()
            yield mock_service

    @pytest.fixture
    def turno(self):
        paciente = Paciente(
            id=1, nombre="Juan", apellido="Perez", dni="12345678", telefono="555-1234"
        )
        profesional = Profesional(
            id=1, nombre="Dra. Garcia", especialidad="Cardiologia",
            duracion_turno=30, horario_inicio="09:00", horario_fin="18:00",
            dias_atencion=["Lunes"]
        )
        return Turno(
            id=1, fecha=date(2025, 6, 15), hora_inicio=time(10, 0),
            hora_fin=time(10, 30), estado="RESERVADO",
            paciente=paciente, profesional=profesional
        )

    def test_create_event_success(self, mock_service, turno):
        """RED: create_event should call Google API and return event_id."""
        from app.config import Settings
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            telegram_bot_token="test",
            google_calendar_credentials='{"type": "service_account"}',
            google_calendar_id="primary",
        )
        mock_events = mock_service.events.return_value
        mock_insert = mock_events.insert.return_value
        mock_insert.execute.return_value = {"id": "event_123"}

        service = CalendarService(settings=settings)
        result = service.create_event(turno)

        assert result == "event_123"
        mock_events.insert.assert_called_once()
        call_kwargs = mock_events.insert.call_args[1]
        assert call_kwargs["calendarId"] == "primary"
        body = call_kwargs["body"]
        assert "Juan" in body["summary"]
        assert "2025-06-15" in body["start"]["dateTime"]

    def test_update_event_success(self, mock_service, turno):
        """RED: update_event should call Google API and return event_id."""
        from app.config import Settings
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            telegram_bot_token="test",
            google_calendar_credentials='{"type": "service_account"}',
            google_calendar_id="primary",
        )
        turno.google_event_id = "event_123"
        mock_events = mock_service.events.return_value
        mock_update = mock_events.update.return_value
        mock_update.execute.return_value = {"id": "event_123"}

        service = CalendarService(settings=settings)
        result = service.update_event(turno)

        assert result == "event_123"
        mock_events.update.assert_called_once()
        call_kwargs = mock_events.update.call_args[1]
        assert call_kwargs["calendarId"] == "primary"
        assert call_kwargs["eventId"] == "event_123"
        body = call_kwargs["body"]
        assert "Juan" in body["summary"]

    def test_delete_event_success(self, mock_service):
        """RED: delete_event should call Google API and return None."""
        from app.config import Settings
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            telegram_bot_token="test",
            google_calendar_credentials='{"type": "service_account"}',
            google_calendar_id="primary",
        )
        mock_events = mock_service.events.return_value
        mock_delete = mock_events.delete.return_value
        mock_delete.execute.return_value = None

        service = CalendarService(settings=settings)
        result = service.delete_event("event_123")

        assert result is None
        mock_events.delete.assert_called_once()
        call_kwargs = mock_events.delete.call_args[1]
        assert call_kwargs["calendarId"] == "primary"
        assert call_kwargs["eventId"] == "event_123"

    def test_create_event_retries_on_500(self, mock_service, turno):
        """RED: create_event should retry on HTTP 500 up to max_retries."""
        from app.config import Settings
        from googleapiclient.errors import HttpError
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            telegram_bot_token="test",
            google_calendar_credentials='{"type": "service_account"}',
            google_calendar_id="primary",
            google_calendar_max_retries=3,
            google_calendar_base_delay=0.1,
            google_calendar_max_delay=0.2,
        )
        mock_events = mock_service.events.return_value
        mock_insert = mock_events.insert.return_value
        # Create a mock HttpError with status 500
        resp = MagicMock()
        resp.status = 500
        http_error = HttpError(resp, b"Internal Server Error")
        mock_insert.execute.side_effect = [http_error, http_error, http_error]

        service = CalendarService(settings=settings)
        with pytest.raises(HttpError) as exc_info:
            service.create_event(turno)
        assert exc_info.value.resp.status == 500
        assert mock_insert.execute.call_count == 3

    def test_create_event_no_retry_on_404(self, mock_service, turno):
        """RED: create_event should NOT retry on HTTP 404."""
        from app.config import Settings
        from googleapiclient.errors import HttpError
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            telegram_bot_token="test",
            google_calendar_credentials='{"type": "service_account"}',
            google_calendar_id="primary",
            google_calendar_max_retries=3,
            google_calendar_base_delay=0.1,
            google_calendar_max_delay=0.2,
        )
        mock_events = mock_service.events.return_value
        mock_insert = mock_events.insert.return_value
        resp = MagicMock()
        resp.status = 404
        http_error = HttpError(resp, b"Not Found")
        mock_insert.execute.side_effect = http_error

        service = CalendarService(settings=settings)
        with pytest.raises(HttpError) as exc_info:
            service.create_event(turno)
        assert exc_info.value.resp.status == 404
        assert mock_insert.execute.call_count == 1

    def test_create_event_idempotent(self, mock_service, turno):
        """RED: second create_event with same turno should call update_event."""
        from app.config import Settings
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            telegram_bot_token="test",
            google_calendar_credentials='{"type": "service_account"}',
            google_calendar_id="primary",
        )
        mock_events = mock_service.events.return_value
        mock_insert = mock_events.insert.return_value
        mock_insert.execute.return_value = {"id": "event_123"}
        mock_update = mock_events.update.return_value
        mock_update.execute.return_value = {"id": "event_123"}

        service = CalendarService(settings=settings)
        # First call creates the event
        result1 = service.create_event(turno)
        assert result1 == "event_123"
        assert mock_insert.execute.call_count == 1
        # Simulate caller assigning google_event_id after first creation
        turno.google_event_id = "event_123"
        # Second call should update instead of insert
        result2 = service.create_event(turno)
        assert result2 == "event_123"
        mock_events.update.assert_called_once()
        # insert should not have been called again
        assert mock_insert.execute.call_count == 1

    def test_credentials_invalid(self, monkeypatch):
        """RED: invalid credentials should raise a clear error on construction."""
        from app.config import Settings
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            telegram_bot_token="test",
            google_calendar_credentials="not-valid-json",
            google_calendar_id="primary",
        )
        with pytest.raises(ValueError) as exc_info:
            CalendarService(settings=settings)
        assert "credenciales" in str(exc_info.value).lower() or "credentials" in str(exc_info.value).lower()
