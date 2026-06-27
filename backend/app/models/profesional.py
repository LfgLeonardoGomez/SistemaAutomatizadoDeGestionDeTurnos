from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import String, JSON, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Profesional(Base):
    __tablename__ = "profesional"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    especialidad: Mapped[str] = mapped_column(String(255), nullable=False)
    duracion_turno: Mapped[int] = mapped_column(nullable=False)
    horario_inicio: Mapped[str] = mapped_column(String(5), nullable=False)
    horario_fin: Mapped[str] = mapped_column(String(5), nullable=False)
    dias_atencion: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(), default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Auth columns (C-14)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    api_key: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Integration tokens (C-14)
    google_refresh_token: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    telegram_bot_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    telegram_secret_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Google Calendar target (C-22)
    google_calendar_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, server_default="primary"
    )

    turnos: Mapped[List["Turno"]] = relationship(
        "Turno", back_populates="profesional", lazy="selectin"
    )
    pacientes: Mapped[List["Paciente"]] = relationship(
        "Paciente", back_populates="profesional", lazy="selectin"
    )
    lista_de_espera: Mapped[List["ListaDeEspera"]] = relationship(
        "ListaDeEspera", back_populates="profesional", lazy="selectin"
    )
