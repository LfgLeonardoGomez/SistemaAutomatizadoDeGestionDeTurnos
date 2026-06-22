from datetime import datetime, timezone, date, time
from typing import Optional

from sqlalchemy import (
    String,
    ForeignKey,
    Index,
    CheckConstraint,
    Date,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Turno(Base):
    __tablename__ = "turno"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    estado: Mapped[str] = mapped_column(
        String(50), nullable=False, default="DISPONIBLE"
    )
    paciente_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("paciente.id", ondelete="SET NULL"), nullable=True
    )
    profesional_id: Mapped[int] = mapped_column(
        ForeignKey("profesional.id", ondelete="CASCADE"), nullable=False
    )
    google_event_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    creado_en: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    paciente: Mapped[Optional["Paciente"]] = relationship(
        "Paciente", back_populates="turnos", lazy="selectin"
    )
    profesional: Mapped["Profesional"] = relationship(
        "Profesional", back_populates="turnos", lazy="selectin"
    )
    reserva_temporal: Mapped[Optional["ReservaTemporal"]] = relationship(
        "ReservaTemporal",
        back_populates="turno",
        lazy="selectin",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        CheckConstraint("hora_fin > hora_inicio", name="ck_turno_horario_valido"),
        Index("ix_turno_fecha_hora_inicio", "fecha", "hora_inicio"),
        Index("ix_turno_estado", "estado"),
        Index("ix_turno_paciente_id_estado", "paciente_id", "estado"),
        Index("ix_turno_google_event_id", "google_event_id"),
    )
