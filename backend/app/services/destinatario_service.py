"""Helpers de destinatarios de notificación de un turno — C-23 TAREA 5.

C-23 TAREA 5: el helper centraliza el upsert de un ``TurnoDestinatario``
por ``(turno_id, canal)``. Esto evita duplicar la lógica de upsert en cada
punto donde se asigna un destinatario (reserva, confirmación, reprogramación)
y respeta la ``UNIQUE(turno_id, canal)`` declarada en el modelo.

Patrón A (transaccional): el helper NO hace commit ni rollback. El caller
(servicio de reserva/confirmación o router) es responsable de invocar
``commit()`` en el happy path y ``rollback()`` ante excepciones. Esto
mantiene la atomicidad de las operaciones de múltiples pasos.
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.turno_destinatario import TurnoDestinatario

logger = logging.getLogger(__name__)


# Canales válidos (deben coincidir con ``canal_notificacion_enum`` del modelo).
# Definidos acá para validar al borde de la API de service sin tener que
# importar el tipo ENUM de SQLAlchemy.
_CANALES_VALIDOS: frozenset[str] = frozenset({"TELEGRAM", "EMAIL"})


async def upsert_destinatario(
    db: AsyncSession,
    turno_id: int,
    canal: str,
    destinatario: str,
) -> TurnoDestinatario:
    """Upsert de un ``TurnoDestinatario`` por ``(turno_id, canal)``.

    - Si ya existe una fila con esa ``(turno_id, canal)``, actualiza el
      ``destinatario`` (in-place) y la retorna.
    - Si no existe, crea una nueva fila y la retorna (sin flush implícito;
      el caller controla el commit).

    Patrón A: no commitea. El caller decide cuándo.

    Raises:
        ValueError: si ``canal`` no es uno de los canales permitidos.
    """
    if canal not in _CANALES_VALIDOS:
        raise ValueError(
            f"canal inválido: {canal!r}. Valores permitidos: {sorted(_CANALES_VALIDOS)}"
        )

    result = await db.execute(
        select(TurnoDestinatario).where(
            TurnoDestinatario.turno_id == turno_id,
            TurnoDestinatario.canal == canal,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        if existing.destinatario != destinatario:
            logger.info(
                f"Upsert destinatario turno {turno_id} canal {canal}: "
                f"{existing.destinatario!r} -> {destinatario!r}"
            )
            existing.destinatario = destinatario
        return existing

    new = TurnoDestinatario(
        turno_id=turno_id,
        canal=canal,
        destinatario=destinatario,
    )
    db.add(new)
    return new
