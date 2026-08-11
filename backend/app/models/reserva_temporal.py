from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, UniqueConstraint, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ReservaTemporal(Base):
    __tablename__ = "reserva_temporal"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    turno_id: Mapped[int] = mapped_column(
        ForeignKey("turno.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    expiracion: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    # C-27: partial answers of the Telegram capture conversation (dni, nombre,
    # apellido, telefono, email). Each bot message is a separate n8n execution,
    # so the answers need a durable home between them. Scoped to the reservation
    # on purpose: the row is deleted on confirmation and by
    # ``liberar_reservas_vencidas``, so the conversation state expires with the
    # slot it belongs to and needs no cleanup of its own.
    datos_captura: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}", default=dict
    )

    turno: Mapped["Turno"] = relationship(
        "Turno", back_populates="reserva_temporal", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_reserva_temporal_expiracion", "expiracion"),
    )
