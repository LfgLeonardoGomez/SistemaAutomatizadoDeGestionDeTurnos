from datetime import datetime, timezone, date

from sqlalchemy import ForeignKey, Date
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
        default=lambda: datetime.now(timezone.utc)
    )
    notificado: Mapped[bool] = mapped_column(default=False, nullable=False)

    paciente: Mapped["Paciente"] = relationship(
        "Paciente", back_populates="lista_de_espera", lazy="selectin"
    )
