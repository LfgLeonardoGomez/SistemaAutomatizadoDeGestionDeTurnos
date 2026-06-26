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
             patch("app.services.calendar_service.Credentials") as mock_creds_cls:
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            mock_creds_cls.return_value = MagicMock()
            yield mock_service

    @pytest.fixture
    def profesional_con_refresh(self):
        return Profesional(
            id=1, nombre="Dra. Garcia", especialidad="Cardiologia",
            duracion_turno=30, horario_inicio="09:00", horario_fin="18:00",
            dias_atencion=["Lunes"],
            google_refresh_token="test_refresh_token",
            google_calendar_id="test_calendar_id",
        )

    @pytest.fixture
    def turno(self, profesional_con_refresh):
        paciente = Paciente(
            id=1, nombre="Juan", apellido="Perez", dni="12345678", telefono="555-1234"
        )
        return Turno(
            id=1, fecha=date(2025, 6, 15), hora_inicio=time(10, 0),
            hora_fin=time(10, 30), estado="RESERVADO",
            paciente=paciente, profesional=profesional_con_refresh
        )

    def test_create_event_success(self, mock_service, turno, profesional_con_refresh):
        """RED: create_event should call Google API and return event_id."""
        from app.config import Settings
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            secret_key="test",
            google_client_id="client_id",
            google_client_secret="client_secret",
        )
        mock_events = mock_service.events.return_value
        mock_insert = mock_events.insert.return_value
        mock_insert.execute.return_value = {"id": "event_123"}

        service = CalendarService(profesional_con_refresh, settings=settings)
        result = service.create_event(turno)

        assert result == "event_123"
        mock_events.insert.assert_called_once()
        call_kwargs = mock_events.insert.call_args[1]
        assert call_kwargs["calendarId"] == "test_calendar_id"
        body = call_kwargs["body"]
        assert "Juan" in body["summary"]
        assert "2025-06-15" in body["start"]["dateTime"]

    def test_update_event_success(self, mock_service, turno, profesional_con_refresh):
        """RED: update_event should call Google API and return event_id."""
        from app.config import Settings
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            secret_key="test",
            google_client_id="client_id",
            google_client_secret="client_secret",
        )
        turno.google_event_id = "event_123"
        mock_events = mock_service.events.return_value
        mock_update = mock_events.update.return_value
        mock_update.execute.return_value = {"id": "event_123"}

        service = CalendarService(profesional_con_refresh, settings=settings)
        result = service.update_event(turno)

        assert result == "event_123"
        mock_events.update.assert_called_once()
        call_kwargs = mock_events.update.call_args[1]
        assert call_kwargs["calendarId"] == "test_calendar_id"
        assert call_kwargs["eventId"] == "event_123"
        body = call_kwargs["body"]
        assert "Juan" in body["summary"]

    def test_delete_event_success(self, mock_service, profesional_con_refresh):
        """RED: delete_event should call Google API and return None."""
        from app.config import Settings
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            secret_key="test",
            google_client_id="client_id",
            google_client_secret="client_secret",
        )
        mock_events = mock_service.events.return_value
        mock_delete = mock_events.delete.return_value
        mock_delete.execute.return_value = None

        service = CalendarService(profesional_con_refresh, settings=settings)
        result = service.delete_event("event_123")

        assert result is None
        mock_events.delete.assert_called_once()
        call_kwargs = mock_events.delete.call_args[1]
        assert call_kwargs["calendarId"] == "test_calendar_id"
        assert call_kwargs["eventId"] == "event_123"

    def test_create_event_retries_on_500(self, mock_service, turno, profesional_con_refresh):
        """RED: create_event should retry on HTTP 500 up to max_retries."""
        from app.config import Settings
        from googleapiclient.errors import HttpError
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            secret_key="test",
            google_client_id="client_id",
            google_client_secret="client_secret",
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

        service = CalendarService(profesional_con_refresh, settings=settings)
        with pytest.raises(HttpError) as exc_info:
            service.create_event(turno)
        assert exc_info.value.resp.status == 500
        assert mock_insert.execute.call_count == 3

    def test_create_event_no_retry_on_404(self, mock_service, turno, profesional_con_refresh):
        """RED: create_event should NOT retry on HTTP 404."""
        from app.config import Settings
        from googleapiclient.errors import HttpError
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            secret_key="test",
            google_client_id="client_id",
            google_client_secret="client_secret",
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

        service = CalendarService(profesional_con_refresh, settings=settings)
        with pytest.raises(HttpError) as exc_info:
            service.create_event(turno)
        assert exc_info.value.resp.status == 404
        assert mock_insert.execute.call_count == 1

    def test_create_event_idempotent(self, mock_service, turno, profesional_con_refresh):
        """RED: second create_event with same turno should call update_event."""
        from app.config import Settings
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            secret_key="test",
            google_client_id="client_id",
            google_client_secret="client_secret",
        )
        mock_events = mock_service.events.return_value
        mock_insert = mock_events.insert.return_value
        mock_insert.execute.return_value = {"id": "event_123"}
        mock_update = mock_events.update.return_value
        mock_update.execute.return_value = {"id": "event_123"}

        service = CalendarService(profesional_con_refresh, settings=settings)
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

    def test_credentials_invalid_sin_refresh_token(self):
        """RED: profesional sin google_refresh_token debe lanzar ValueError."""
        from app.config import Settings
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            secret_key="test",
            google_client_id="client_id",
            google_client_secret="client_secret",
        )
        profesional_sin_token = Profesional(
            id=2, nombre="Dr. Sin Token", especialidad="Test",
            duracion_turno=30, horario_inicio="08:00", horario_fin="18:00",
            dias_atencion=["Lunes"],
            google_refresh_token=None,
        )
        with pytest.raises(ValueError) as exc_info:
            CalendarService(profesional_sin_token, settings=settings)
        assert "no tiene google_refresh_token" in str(exc_info.value).lower()

    def test_credentials_invalid_refresh_token_vacio(self):
        """RED: profesional con google_refresh_token vacío debe lanzar ValueError."""
        from app.config import Settings
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            secret_key="test",
            google_client_id="client_id",
            google_client_secret="client_secret",
        )
        profesional_vacio = Profesional(
            id=3, nombre="Dr. Vacio", especialidad="Test",
            duracion_turno=30, horario_inicio="08:00", horario_fin="18:00",
            dias_atencion=["Lunes"],
            google_refresh_token="",
        )
        with pytest.raises(ValueError) as exc_info:
            CalendarService(profesional_vacio, settings=settings)
        assert "no tiene google_refresh_token" in str(exc_info.value).lower()

    def test_create_event_fallback_to_primary_when_no_calendar_id(
        self, mock_service, turno
    ):
        """RED: create_event falls back to 'primary' when professional has no google_calendar_id."""
        from app.config import Settings

        # Professional without google_calendar_id — fallback to "primary"
        profesional_sin_calendar = Profesional(
            id=10, nombre="Dra. Sin Calendar", especialidad="Cardiologia",
            duracion_turno=30, horario_inicio="09:00", horario_fin="18:00",
            dias_atencion=["Lunes"],
            google_refresh_token="test_refresh_token",
            google_calendar_id=None,
        )
        # Rebind turno to this professional
        turno.profesional = profesional_sin_calendar

        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            secret_key="test",
            google_client_id="client_id",
            google_client_secret="client_secret",
        )
        mock_events = mock_service.events.return_value
        mock_insert = mock_events.insert.return_value
        mock_insert.execute.return_value = {"id": "event_fallback"}

        service = CalendarService(profesional_sin_calendar, settings=settings)
        result = service.create_event(turno)

        assert result == "event_fallback"
        call_kwargs = mock_events.insert.call_args[1]
        assert call_kwargs["calendarId"] == "primary"
