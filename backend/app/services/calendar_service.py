import json
import logging
from datetime import datetime
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.config import Settings
from app.models.turno import Turno

logger = logging.getLogger(__name__)


def _is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, HttpError):
        return exc.resp.status >= 500
    return isinstance(exc, (TimeoutError, ConnectionError))


class CalendarService:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        try:
            creds_info = json.loads(self.settings.google_calendar_credentials)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "GOOGLE_CALENDAR_CREDENTIALS no contiene un JSON válido"
            ) from exc
        if not isinstance(creds_info, dict) or not creds_info:
            raise ValueError(
                "GOOGLE_CALENDAR_CREDENTIALS está vacío o no es un objeto JSON válido"
            )
        try:
            credentials = Credentials.from_service_account_info(creds_info)
        except Exception as exc:
            raise ValueError(
                "No se pudieron cargar las credenciales de Google Calendar: "
                f"{exc}"
            ) from exc
        self._service = build("calendar", "v3", credentials=credentials)

        _retry = retry(
            stop=stop_after_attempt(self.settings.google_calendar_max_retries),
            wait=wait_exponential_jitter(
                initial=self.settings.google_calendar_base_delay,
                max=self.settings.google_calendar_max_delay,
            ),
            retry=retry_if_exception(_is_retryable_error),
            reraise=True,
        )
        self.create_event = _retry(self.create_event)
        self.update_event = _retry(self.update_event)
        self.delete_event = _retry(self.delete_event)

    def _make_event_body(self, turno: Turno) -> dict:
        paciente = turno.paciente
        profesional = turno.profesional
        summary = f"Turno: {paciente.nombre} {paciente.apellido} con {profesional.nombre}"
        description = f"DNI: {paciente.dni} | Tel: {paciente.telefono}"
        start_dt = datetime.combine(turno.fecha, turno.hora_inicio)
        end_dt = datetime.combine(turno.fecha, turno.hora_fin)
        return {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "America/Argentina/Buenos_Aires"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "America/Argentina/Buenos_Aires"},
        }

    def create_event(self, turno: Turno) -> str:
        existing_id = getattr(turno, "google_event_id", None)
        if existing_id:
            return self.update_event(turno)
        body = self._make_event_body(turno)
        result = self._service.events().insert(
            calendarId=self.settings.google_calendar_id,
            body=body,
        ).execute()
        event_id = result["id"]
        logger.info(f"Evento creado: {event_id} para turno {turno.id}")
        return event_id

    def update_event(self, turno: Turno) -> str:
        event_id = getattr(turno, "google_event_id", None)
        if not event_id:
            raise ValueError("Turno no tiene google_event_id")
        body = self._make_event_body(turno)
        result = self._service.events().update(
            calendarId=self.settings.google_calendar_id,
            eventId=event_id,
            body=body,
        ).execute()
        logger.info(f"Evento actualizado: {event_id} para turno {turno.id}")
        return result["id"]

    def delete_event(self, event_id: str) -> None:
        self._service.events().delete(
            calendarId=self.settings.google_calendar_id,
            eventId=event_id,
        ).execute()
        logger.info(f"Evento eliminado: {event_id}")
