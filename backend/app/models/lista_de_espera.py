from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy import ForeignKey, Date, Index, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ListaDeEspera(Base):
    __tablename__ = "lista_de_espera"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    paciente_id: Mapped[int] = mapped_column(
        ForeignKey("paciente.id", ondelete="CASCADE"),
        nullable=False,
    )
    fecha_solicitada: Mapped[date] = mapped_column(Date, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    notificado: Mapped[bool] = mapped_column(default=False, nullable=False)
    turno_ofrecido_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("turno.id", ondelete="SET NULL"),
        nullable=True,
    )
    notificado_en: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(nullable=True)

    profesional_id: Mapped[int] = mapped_column(
        ForeignKey("profesional.id", ondelete="CASCADE"), nullable=False
    )
    profesional: Mapped["Profesional"] = relationship(
        "Profesional", back_populates="lista_de_espera", lazy="selectin"
    )

    paciente: Mapped["Paciente"] = relationship(
        "Paciente", back_populates="lista_de_espera", lazy="selectin"
    )
    turno_ofrecido: Mapped[Optional["Turno"]] = relationship(
        "Turno", lazy="selectin"
    )

    __table_args__ = (
        Index(
            "ix_lista_de_espera_profesional_paciente",
            "profesional_id",
            "paciente_id",
        ),
    )
