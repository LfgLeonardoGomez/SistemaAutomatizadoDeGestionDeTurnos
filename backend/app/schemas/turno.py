from datetime import date, time, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class SlotResponse(BaseModel):
    hora_inicio: str
    hora_fin: str
    disponible: bool


class ReservaTurnoRequest(BaseModel):
    """Request de reserva temporal de un turno.

    C-23 TAREA 4: agrega ``telegram_chat_id`` opcional. El bot de Telegram
    conoce el ``chat_id`` del mensaje que disparó la reserva, y lo envía
    al backend para que el turno sepa a qué contacto notificar. El campo
    es retrocompatible: requests que no lo incluyan siguen siendo válidas
    (la reserva queda sin destinatario TELEGRAM; el recordatorio no se
    envía y se loguea un warning, ver ``notificacion_service``).
    """
    fecha: date
    hora_inicio: time
    paciente_id: Optional[int] = None
    telegram_chat_id: Optional[str] = None


class ConfirmarTurnoRequest(BaseModel):
    """Request de confirmación de un turno reservado.

    C-23 TAREA 4: agrega ``telegram_chat_id`` opcional. El flujo n8n conoce
    el ``chat_id`` del update de Telegram que disparó la confirmación, y
    lo pasa al backend para registrar/actualizar el destinatario TELEGRAM
    del turno (``upsert`` por ``(turno_id, canal)``). El campo ``email``
    ya existía y modela el destinatario EMAIL (también opcional).

    Ambos canales son opcionales y retrocompatibles. Un turno puede tener
    0, 1 o 2 destinatarios.
    """
    nombre: str
    apellido: str
    dni: str
    telefono: str
    email: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class ReprogramarTurnoRequest(BaseModel):
    nueva_fecha: date
    nueva_hora_inicio: time
    paciente_data: Optional[ConfirmarTurnoRequest] = None


class TurnoDestinatarioRead(BaseModel):
    """Schema de lectura de un destinatario de notificación de un turno.

    C-23 TAREA 4.2: modela ``(id, canal, destinatario)`` de un
    ``TurnoDestinatario``. ``canal`` se valida contra el ENUM
    ``canal_notificacion_enum`` ('TELEGRAM', 'EMAIL') para que un valor
    inválido no llegue al cliente sin ser detectado.

    Decisión confirmada (OQ-2): destinatario INTERNO. Este schema existe
    para uso interno del backend y para que tests/clientes que necesiten
    explícitamente los destinatarios puedan serializarlos, pero NO se
    incluye en ``TurnoResponse`` (la API REST no expone destinatarios).
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    canal: str
    destinatario: str

    @field_validator("canal")
    @classmethod
    def validar_canal(cls, v: str) -> str:
        if v not in {"TELEGRAM", "EMAIL"}:
            raise ValueError(
                f"canal inválido: {v}. Valores permitidos: TELEGRAM, EMAIL"
            )
        return v


class TurnoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: date
    hora_inicio: time
    hora_fin: time
    estado: str
    profesional_id: int
    paciente_id: Optional[int] = None
    google_event_id: Optional[str] = None
    creado_en: datetime

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: str) -> str:
        if v not in {"DISPONIBLE", "RESERVADO_TEMPORAL", "CONFIRMADO", "CANCELADO", "COMPLETADO"}:
            raise ValueError(f"estado inválido: {v}")
        return v
