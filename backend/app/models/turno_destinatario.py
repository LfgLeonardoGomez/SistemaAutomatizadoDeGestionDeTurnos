from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TurnoDestinatario(Base):
    """Destinatario de notificación para un turno en un canal específico.

    Modela la relación turno → canal → contacto de forma extensible:
    - Un turno puede tener 0..N destinatarios (uno por canal).
    - UNIQUE(turno_id, canal) garantiza a lo sumo un destinatario por canal por turno.
    - FK con ondelete="CASCADE": al borrar el Turno se borran sus destinatarios.

    Sigue el precedente de ListaDeEspera (contacto por registro, no por paciente).
    El scope de tenant se alcanza vía turno.profesional_id; no se necesita
    profesional_id propio en esta tabla.
    """

    __tablename__ = "turno_destinatario"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    turno_id: Mapped[int] = mapped_column(
        ForeignKey("turno.id", ondelete="CASCADE"), nullable=False
    )
    canal: Mapped[str] = mapped_column(
        SAEnum(
            "TELEGRAM",
            "EMAIL",
            name="canal_notificacion_enum",
            create_type=False,  # El tipo es creado explícitamente en la migración
            native_enum=True,
        ),
        nullable=False,
    )
    destinatario: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(),
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    turno: Mapped["Turno"] = relationship("Turno", back_populates="destinatarios")

    __table_args__ = (
        UniqueConstraint("turno_id", "canal", name="uq_turno_destinatario_canal"),
        Index("ix_turno_destinatario_turno_id", "turno_id"),
    )
