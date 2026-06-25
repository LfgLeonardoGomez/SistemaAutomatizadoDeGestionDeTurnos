from datetime import datetime

from pydantic import BaseModel, EmailStr


class SuperAdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfesionalAdminResponse(BaseModel):
    id: int
    nombre: str
    especialidad: str
    email: str | None
    is_active: bool
    creado_en: datetime

    model_config = {"from_attributes": True}


class GlobalMetricsResponse(BaseModel):
    total_profesionales: int
    profesionales_activos: int
    profesionales_inactivos: int
    total_turnos: int
    turnos_hoy: int
    turnos_confirmados_30d: int
    turnos_cancelados_30d: int
    total_pacientes: int
    tasa_confirmacion_30d: float
    tasa_cancelacion_30d: float
