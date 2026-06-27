from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import String, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Paciente(Base):
    __tablename__ = "paciente"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    apellido: Mapped[str] = mapped_column(String(255), nullable=False)
    dni: Mapped[str] = mapped_column(String(50), nullable=False)
    telefono: Mapped[str] = mapped_column(String(50), nullable=False)
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(), default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    profesional_id: Mapped[int] = mapped_column(
        ForeignKey("profesional.id", ondelete="CASCADE"), nullable=False
    )
    profesional: Mapped["Profesional"] = relationship(
        "Profesional", back_populates="pacientes", lazy="selectin"
    )

    turnos: Mapped[List["Turno"]] = relationship(
        "Turno", back_populates="paciente", lazy="selectin"
    )
    lista_de_espera: Mapped[List["ListaDeEspera"]] = relationship(
        "ListaDeEspera", back_populates="paciente", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint(
            "profesional_id", "dni", name="uq_paciente_profesional_dni"
        ),
    )
