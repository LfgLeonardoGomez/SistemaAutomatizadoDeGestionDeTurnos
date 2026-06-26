from datetime import date, time
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class PacienteInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    apellido: str
    dni: str
    telefono: str


class ProfesionalConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    horario_inicio: str
    horario_fin: str
    dias_atencion: list[str]
    duracion_turno: int
    especialidad: str


class ProfesionalConfigUpdate(BaseModel):
    horario_inicio: Optional[str] = None
    horario_fin: Optional[str] = None
    dias_atencion: Optional[list[str]] = None
    duracion_turno: Optional[int] = None

    @model_validator(mode="after")
    def check_horarios(self):
        if self.horario_inicio is not None and self.horario_fin is not None:
            h_inicio = time.fromisoformat(self.horario_inicio)
            h_fin = time.fromisoformat(self.horario_fin)
            if h_inicio >= h_fin:
                raise ValueError("horario_inicio debe ser menor a horario_fin")
        return self

    @field_validator("duracion_turno")
    @classmethod
    def check_duracion(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("duracion_turno debe ser positiva")
        return v

    @field_validator("dias_atencion")
    @classmethod
    def check_dias(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("dias_atencion debe contener al menos un día")
            validos = {
                "Lunes",
                "Martes",
                "Miércoles",
                "Jueves",
                "Viernes",
                "Sábado",
                "Domingo",
            }
            for dia in v:
                if dia not in validos:
                    raise ValueError(f"dias_atencion contiene valor inválido: {dia}")
        return v


class DisponibilidadResponse(BaseModel):
    horarios: list[str]


class ProfesionalTurnoHoyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fecha: date
    hora_inicio: time
    hora_fin: time
    estado: str
    profesional_id: int
    paciente_id: Optional[int] = None
    paciente: Optional[PacienteInfoResponse] = None


class ProfesionalMetricasResponse(BaseModel):
    turnos_hoy: int
    tasa_confirmacion_30d: float
    tasa_cancelacion_30d: float


class ProfesionalIntegracionesUpdate(BaseModel):
    telegram_bot_token: Optional[str] = None
    google_refresh_token: Optional[str] = None
    google_calendar_id: Optional[str] = None

    @field_validator("telegram_bot_token", "google_refresh_token", "google_calendar_id")
    @classmethod
    def reject_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() == "":
            raise ValueError("token cannot be empty")
        return v


class ProfesionalIntegracionesResponse(BaseModel):
    has_telegram: bool
    has_google: bool
    google_calendar_id: str


class ProfesionalCreateRequest(BaseModel):
    nombre: str
    email: EmailStr
    password: str = Field(..., min_length=8)
    especialidad: str


class ProfesionalCreateResponse(BaseModel):
    id: int
    nombre: str
    email: str
    especialidad: str
    is_active: bool
    duracion_turno: int
    horario_inicio: str
    horario_fin: str
    dias_atencion: list[str]
    api_key: str
    telegram_secret_token: str

    model_config = ConfigDict(from_attributes=True)
