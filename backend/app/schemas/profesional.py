from datetime import time
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


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
