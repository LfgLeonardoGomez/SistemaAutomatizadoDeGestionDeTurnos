from pydantic import BaseModel, EmailStr, Field


class ProfesionalRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    nombre: str
    especialidad: str
    duracion_turno: int = Field(..., gt=0)
    horario_inicio: str
    horario_fin: str
    dias_atencion: list[str]


class ProfesionalLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApiKeyResponse(BaseModel):
    api_key: str
