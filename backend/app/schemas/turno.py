from datetime import date, time, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class SlotResponse(BaseModel):
    hora_inicio: str
    hora_fin: str
    disponible: bool


class ReservaTurnoRequest(BaseModel):
    fecha: date
    hora_inicio: time
    paciente_id: Optional[int] = None


class ConfirmarTurnoRequest(BaseModel):
    nombre: str
    apellido: str
    dni: str
    telefono: str
    email: Optional[str] = None


class ReprogramarTurnoRequest(BaseModel):
    nueva_fecha: date
    nueva_hora_inicio: time
    paciente_data: Optional[ConfirmarTurnoRequest] = None


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
