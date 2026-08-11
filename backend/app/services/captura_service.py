"""Conversational capture state for the Telegram booking flow (C-27).

The bot asks for the patient's DNI and, when the patient is new, for name and
phone. Every answer arrives as a separate Telegram update, which n8n runs as a
separate execution, so the partial answers cannot live in the workflow's
memory: they are persisted on ``reserva_temporal.datos_captura``.

The chat is resolved to its booking through the ``TurnoDestinatario`` row that
``turno_service.reservar_turno`` already writes for a Telegram reservation —
no extra chat-to-turno mapping is introduced.
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import CapturaNoEncontradaError
from app.models.reserva_temporal import ReservaTemporal
from app.models.turno import Turno
from app.models.turno_destinatario import TurnoDestinatario
from app.services.turno_service import _utcnow_naive

# Fields required before the booking can be confirmed. ``email`` is absent on
# purpose: it is optional for the patient and never blocks confirmation.
_CAMPOS_NOMBRE = ("nombre", "apellido")
_PASO_DNI = "dni"
_PASO_NOMBRE = "nombre"
_PASO_TELEFONO = "telefono"
_PASO_CONFIRMAR = "confirmar"


@dataclass(frozen=True)
class CapturaPendiente:
    """A booking waiting for the patient's data, and how far along it is."""

    turno_id: int
    paso: str
    datos: dict


def derivar_paso(datos: Optional[dict]) -> str:
    """Return the next question to ask, derived from what was captured.

    The step is never stored. Deriving it means a state like ``paso ==
    'telefono'`` with no DNI captured cannot exist in the first place.
    """
    datos = datos or {}

    if not datos.get(_PASO_DNI):
        return _PASO_DNI
    # Name and surname are asked in a single message, so a half-filled pair
    # re-asks the pair rather than moving on with a partial name.
    if not all(datos.get(campo) for campo in _CAMPOS_NOMBRE):
        return _PASO_NOMBRE
    if not datos.get(_PASO_TELEFONO):
        return _PASO_TELEFONO
    return _PASO_CONFIRMAR


def _a_captura(turno_id: int, datos: Optional[dict]) -> CapturaPendiente:
    datos = dict(datos or {})
    return CapturaPendiente(
        turno_id=turno_id, paso=derivar_paso(datos), datos=datos
    )


async def obtener_captura_pendiente(
    db: AsyncSession,
    profesional_id: int,
    telegram_chat_id: str,
) -> Optional[CapturaPendiente]:
    """Return the live capture for this chat, or ``None``.

    "Live" means: a turno of THIS professional, still RESERVADO_TEMPORAL,
    whose reservation has not expired, reachable from ``telegram_chat_id``.
    An expired reservation is not a pending capture — otherwise the bot would
    keep asking for a DNI for a slot it no longer holds.
    """
    stmt = (
        select(ReservaTemporal.turno_id, ReservaTemporal.datos_captura)
        .join(Turno, Turno.id == ReservaTemporal.turno_id)
        .join(TurnoDestinatario, TurnoDestinatario.turno_id == Turno.id)
        .where(
            Turno.profesional_id == profesional_id,
            Turno.estado == "RESERVADO_TEMPORAL",
            ReservaTemporal.expiracion > _utcnow_naive(),
            TurnoDestinatario.canal == "TELEGRAM",
            TurnoDestinatario.destinatario == telegram_chat_id,
        )
        # A chat should only ever hold one reservation at a time, but if a
        # previous one somehow lingers, the newest is the one being answered.
        .order_by(Turno.creado_en.desc(), Turno.id.desc())
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    return _a_captura(row.turno_id, row.datos_captura)


async def actualizar_datos_captura(
    db: AsyncSession,
    profesional_id: int,
    turno_id: int,
    nuevos_datos: dict,
) -> CapturaPendiente:
    """Merge ``nuevos_datos`` into the capture and return the new state.

    Merging rather than replacing is what lets each answer be sent on its own:
    the phone reply must not wipe the DNI captured two messages earlier.

    Raises ``CapturaNoEncontradaError`` when there is no live capture for this
    professional and turno.
    """
    stmt = (
        select(ReservaTemporal)
        .join(Turno, Turno.id == ReservaTemporal.turno_id)
        .where(
            ReservaTemporal.turno_id == turno_id,
            Turno.profesional_id == profesional_id,
            Turno.estado == "RESERVADO_TEMPORAL",
            ReservaTemporal.expiracion > _utcnow_naive(),
        )
        .with_for_update(of=ReservaTemporal)
    )
    reserva = (await db.execute(stmt)).scalar_one_or_none()
    if reserva is None:
        raise CapturaNoEncontradaError()

    # Rebind instead of mutating: SQLAlchemy does not track in-place changes to
    # a JSONB dict, so mutating it would silently not persist.
    reserva.datos_captura = {**(reserva.datos_captura or {}), **(nuevos_datos or {})}
    await db.flush()

    return _a_captura(turno_id, reserva.datos_captura)
