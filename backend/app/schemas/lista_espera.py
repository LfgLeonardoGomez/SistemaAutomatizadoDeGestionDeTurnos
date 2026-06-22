from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ListaEsperaCreate(BaseModel):
    paciente_id: int
    fecha_solicitada: date
    telegram_chat_id: Optional[str] = None


class ListaEsperaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    fecha_solicitada: date
    creado_en: datetime
    notificado: bool
    turno_ofrecido_id: Optional[int] = None
    notificado_en: Optional[datetime] = None
    telegram_chat_id: Optional[str] = None
