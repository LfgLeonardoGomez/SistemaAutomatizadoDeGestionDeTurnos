from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, UniqueConstraint, DateTime
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

    turno: Mapped["Turno"] = relationship(
        "Turno", back_populates="reserva_temporal", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_reserva_temporal_expiracion", "expiracion"),
    )
