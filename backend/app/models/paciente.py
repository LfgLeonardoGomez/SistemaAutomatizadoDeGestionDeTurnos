from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Paciente(Base):
    __tablename__ = "paciente"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    apellido: Mapped[str] = mapped_column(String(255), nullable=False)
    dni: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    telefono: Mapped[str] = mapped_column(String(50), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    turnos: Mapped[List["Turno"]] = relationship(
        "Turno", back_populates="paciente", lazy="selectin"
    )
    lista_de_espera: Mapped[List["ListaDeEspera"]] = relationship(
        "ListaDeEspera", back_populates="paciente", lazy="selectin"
    )
