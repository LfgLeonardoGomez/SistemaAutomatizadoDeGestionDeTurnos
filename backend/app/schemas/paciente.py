from datetime import date, time, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TurnoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: date
    hora_inicio: time
    hora_fin: time
    estado: str
    profesional_id: int
    paciente_id: Optional[int] = None
    creado_en: datetime


class PacienteCreate(BaseModel):
    nombre: str
    apellido: str
    dni: str
    telefono: str


class PacienteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    apellido: str
    dni: str
    telefono: str
    creado_en: datetime


class PacienteConHistorial(PacienteRead):
    turnos: list[TurnoRead] = []


class PacienteBusqueda(BaseModel):
    """Respuesta de ``GET /pacientes/buscar`` — c-27 patient-dni-lookup.

    Deliberadamente no incluye ``creado_en``: el spec solo exige
    ``id``, ``nombre``, ``apellido``, ``dni`` y ``telefono`` (lo mínimo
    para que un cliente conversacional confirme un paciente existente
    sin re-solicitar sus datos).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    apellido: str
    dni: str
    telefono: str
