import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profesional import Profesional
from app.models.lista_de_espera import ListaDeEspera
from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from app.exceptions import (
    TurnoNoEncontradoError,
    TurnoNoDisponibleError,
    TurnoExpiradoError,
)
from app.services.telegram_service import enviar_notificacion_lista_espera
from app.services.availability_service import calcular_disponibilidad
from app.config import Settings

logger = logging.getLogger(__name__)


def _utcnow_naive() -> datetime:
    """Retorna el momento actual como ``datetime`` naive en UTC.

    Patrón consistente con ``turno_service._utcnow_naive`` para todas las
    comparaciones de expiración y timestamps persistidos.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def registrar_en_lista_espera(
    db: AsyncSession,
    profesional_id: int,
    paciente_id: int,
    fecha_solicitada: date,
    telegram_chat_id: Optional[str] = None,
) -> ListaDeEspera:
    """Register a patient in the waiting list for a specific date."""
    result = await db.execute(
        select(Paciente).where(
            Paciente.id == paciente_id, Paciente.profesional_id == profesional_id
        )
    )
    paciente = result.scalar_one_or_none()
    if paciente is None:
        raise TurnoNoEncontradoError("Paciente no encontrado")

    registro = ListaDeEspera(
        paciente_id=paciente_id,
        fecha_solicitada=fecha_solicitada,
        telegram_chat_id=telegram_chat_id,
        profesional_id=profesional_id,
    )
    db.add(registro)
    # Patrón A: el caller (router) hace commit. No hacer commit aquí.
    await db.flush()
    return registro


async def eliminar_de_lista_espera(
    db: AsyncSession, profesional_id: int, lista_espera_id: int
) -> None:
    """Remove a patient from the waiting list. Patrón A: no hace commit."""
    result = await db.execute(
        select(ListaDeEspera).where(
            ListaDeEspera.id == lista_espera_id,
            ListaDeEspera.profesional_id == profesional_id,
        )
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        raise TurnoNoEncontradoError("Registro de lista de espera no encontrado")

    await db.delete(registro)
    # Patrón A: el caller hace commit.


async def obtener_siguiente_paciente_fifo(
    db: AsyncSession, profesional_id: int, fecha: date
) -> Optional[ListaDeEspera]:
    """Atomically select the next patient in FIFO order for a given date."""
    result = await db.execute(
        select(ListaDeEspera)
        .where(
            ListaDeEspera.profesional_id == profesional_id,
            ListaDeEspera.fecha_solicitada == fecha,
            ListaDeEspera.notificado == False,
        )
        .order_by(ListaDeEspera.creado_en.asc())
        .with_for_update()
        .limit(1)
    )
    return result.scalar_one_or_none()


async def notificar_y_marcar(
    db: AsyncSession,
    profesional_id: int,
    lista_espera_id: int,
    turno_id: int,
    chat_id: Optional[str],
) -> None:
    """Atomically mark the waiting-list record as notified and send Telegram message.

    If Telegram sending fails, the DB is NOT updated so the next evaluation
    will retry with the same patient.
    """
    result = await db.execute(
        select(ListaDeEspera)
        .where(
            ListaDeEspera.id == lista_espera_id,
            ListaDeEspera.profesional_id == profesional_id,
        )
        .with_for_update()
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        raise TurnoNoEncontradoError("Registro de lista de espera no encontrado")

    result_turno = await db.execute(
        select(Turno).where(Turno.id == turno_id, Turno.profesional_id == profesional_id)
    )
    turno = result_turno.scalar_one_or_none()
    if turno is None:
        raise TurnoNoEncontradoError("Turno no encontrado")

    if not chat_id:
        logger.warning(
            "No hay chat_id para notificar al paciente %s de lista de espera %s",
            registro.paciente_id,
            registro.id,
        )
        # Without chat_id we cannot notify; leave notificado=False so the job
        # or next cancellation can retry (or eventually a manual path).
        return

    try:
        # Get bot token for this profesional
        result_prof = await db.execute(select(Profesional).where(Profesional.id == profesional_id))
        profesional = result_prof.scalar_one_or_none()
        bot_token = profesional.telegram_bot_token if profesional else None
        if not bot_token:
            logger.warning("Profesional %s no tiene telegram_bot_token", profesional_id)
            return

        ok = await enviar_notificacion_lista_espera(chat_id, turno, bot_token)
        if not ok:
            raise RuntimeError("Telegram notification returned False")
    except Exception as exc:
        logger.error(
            "Fallo al enviar notificación de lista de espera a %s: %s",
            chat_id,
            exc,
        )
        # Do NOT update DB on failure
        return

    registro.notificado = True
    registro.turno_ofrecido_id = turno_id
    registro.notificado_en = _utcnow_naive()
    # Patrón A: el caller (evaluar_lista_espera o router) hace commit.


async def aceptar_turno_lista_espera(
    db: AsyncSession, profesional_id: int, lista_espera_id: int
) -> Turno:
    """Accept the offered slot, confirm the turno, and remove from queue."""
    result = await db.execute(
        select(ListaDeEspera)
        .where(
            ListaDeEspera.id == lista_espera_id,
            ListaDeEspera.profesional_id == profesional_id,
        )
        .with_for_update()
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        raise TurnoNoEncontradoError("Registro de lista de espera no encontrado")

    paciente = registro.paciente
    if paciente is None:
        raise TurnoNoEncontradoError("Paciente no encontrado")

    turno_ofrecido_id = registro.turno_ofrecido_id
    if turno_ofrecido_id is None:
        raise TurnoNoDisponibleError("No hay turno ofrecido")

    # The offered turno may be RESERVADO_TEMPORAL (if created by evaluar_lista_espera)
    # or CANCELADO (if it was the original cancelled turno).  If it is not
    # RESERVADO_TEMPORAL we need to create a fresh reservation for the same slot.
    result_turno = await db.execute(
        select(Turno)
        .where(Turno.id == turno_ofrecido_id, Turno.profesional_id == profesional_id)
        .with_for_update()
    )
    turno_ofrecido = result_turno.scalar_one_or_none()
    if turno_ofrecido is None:
        raise TurnoNoDisponibleError("El turno ofrecido ya no existe")

    # Lazy import to avoid circular dependency
    from app.services.turno_service import reservar_turno, confirmar_turno

    paciente_data = {
        "nombre": paciente.nombre,
        "apellido": paciente.apellido,
        "dni": paciente.dni,
        "telefono": paciente.telefono,
    }

    try:
        if turno_ofrecido.estado == "RESERVADO_TEMPORAL":
            # Directly confirm the existing temporary reservation
            confirmado = await confirmar_turno(
                db, profesional_id=profesional_id, turno_id=turno_ofrecido.id, paciente_data=paciente_data
            )
        else:
            # For cancelled (or any other non-reservable) turnos, create a new one
            nuevo_turno = await reservar_turno(
                db,
                profesional_id=profesional_id,
                fecha=turno_ofrecido.fecha,
                hora_inicio=turno_ofrecido.hora_inicio,
                paciente_id=paciente.id,
            )
            confirmado = await confirmar_turno(
                db, profesional_id=profesional_id, turno_id=nuevo_turno.id, paciente_data=paciente_data
            )
    except TurnoExpiradoError:
        # La reserva temporal ofrecida expiró entre la notificación y la
        # aceptación. Resetear el registro y re-ofrecer al siguiente paciente.
        logger.info(
            "Reserva temporal expirada al aceptar oferta de lista de espera %s; "
            "re-evaluando cola",
            lista_espera_id,
        )
        await _reset_y_reofertar_lista_espera(
            db,
            profesional_id=profesional_id,
            registro=registro,
            turno_id=turno_ofrecido.id,
        )
        # Propagar la excepción al router (que la traduce a 409 Conflict).
        raise

    # Remove from waiting list. Patrón A: caller hace commit.
    await db.delete(registro)
    return confirmado


async def _reset_y_reofertar_lista_espera(
    db: AsyncSession,
    profesional_id: int,
    registro: ListaDeEspera,
    turno_id: int,
) -> None:
    """Resetea un registro de lista de espera y re-llama a ``evaluar_lista_espera``.

    Se usa cuando la reserva temporal ofrecida a un paciente de lista de espera
    expiró entre la notificación y la aceptación. El flujo es:
    1. Liberar el slot (turno → ``DISPONIBLE``, ``paciente_id = None``).
    2. Eliminar la ``ReservaTemporal`` asociada.
    3. Resetear el registro (notificado=False, turno_ofrecido_id=None,
       notificado_en=None, creado_en=now-UTC).
    4. Re-llamar a ``evaluar_lista_espera`` para ofrecer al siguiente paciente.

    No hace commit (Patrón A).
    """
    from app.services.lista_espera_service import evaluar_lista_espera

    # Liberar el slot si sigue siendo RESERVADO_TEMPORAL
    result_turno = await db.execute(
        select(Turno)
        .where(Turno.id == turno_id, Turno.profesional_id == profesional_id)
        .with_for_update()
    )
    turno = result_turno.scalar_one_or_none()
    if turno is not None and turno.estado == "RESERVADO_TEMPORAL":
        turno.estado = "DISPONIBLE"
        turno.paciente_id = None
        await db.execute(
            delete(ReservaTemporal).where(ReservaTemporal.turno_id == turno_id)
        )

    # Resetear el registro
    registro.notificado = False
    registro.turno_ofrecido_id = None
    registro.notificado_en = None
    registro.creado_en = _utcnow_naive()

    # Re-llamar para ofrecer al siguiente paciente (Patrón A: caller hace commit)
    await evaluar_lista_espera(
        db,
        profesional_id=profesional_id,
        fecha=registro.fecha_solicitada,
        turno_id=turno_id,
    )


async def rechazar_turno_lista_espera(
    db: AsyncSession, profesional_id: int, lista_espera_id: int, turno_id: int
) -> None:
    """Reject the offered slot, reset the record, and offer to next patient."""
    result = await db.execute(
        select(ListaDeEspera)
        .where(
            ListaDeEspera.id == lista_espera_id,
            ListaDeEspera.profesional_id == profesional_id,
        )
        .with_for_update()
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        raise TurnoNoEncontradoError("Registro de lista de espera no encontrado")

    # Free the offered turno if it is a temporary reservation
    result_turno = await db.execute(
        select(Turno)
        .where(Turno.id == turno_id, Turno.profesional_id == profesional_id)
        .with_for_update()
    )
    turno = result_turno.scalar_one_or_none()
    if turno is not None and turno.estado == "RESERVADO_TEMPORAL":
        turno.estado = "DISPONIBLE"
        turno.paciente_id = None
        await db.execute(
            delete(ReservaTemporal).where(ReservaTemporal.turno_id == turno_id)
        )

    fecha = registro.fecha_solicitada
    registro.notificado = False
    registro.turno_ofrecido_id = None
    registro.notificado_en = None
    registro.creado_en = _utcnow_naive()
    # Patrón A: el caller (router) hace commit. No hacer commit aquí.

    await evaluar_lista_espera(db, profesional_id=profesional_id, fecha=fecha, turno_id=turno_id)


async def evaluar_lista_espera(
    db: AsyncSession,
    profesional_id: int,
    fecha: date,
    turno_id: Optional[int] = None,
) -> Optional[Turno]:
    """Evaluate the waiting list for a freed slot and notify the next patient.

    If *turno_id* is provided the slot info (fecha/hora) is read from that turno.
    Otherwise the first available slot on *fecha* is picked.
    """
    siguiente = await obtener_siguiente_paciente_fifo(db, profesional_id=profesional_id, fecha=fecha)
    if siguiente is None:
        logger.info("No hay pacientes en lista de espera para la fecha %s", fecha)
        return None

    # Determine which slot to reserve
    if turno_id is not None:
        result = await db.execute(
            select(Turno).where(Turno.id == turno_id, Turno.profesional_id == profesional_id)
        )
        turno_origen = result.scalar_one_or_none()
        if turno_origen is None:
            logger.warning("Turno origen %s no encontrado; no se puede evaluar lista de espera", turno_id)
            return None
        slot_fecha = turno_origen.fecha
        slot_hora = turno_origen.hora_inicio
    else:
        # Pick first available slot on the date for this profesional
        disponibles = await calcular_disponibilidad(db, fecha, profesional_id)
        if not disponibles:
            logger.info("No hay slots disponibles para la fecha %s", fecha)
            return None
        slot_fecha = fecha
        from datetime import time as dt_time
        slot_hora = dt_time.fromisoformat(disponibles[0])

    # Lazy import to avoid circular dependency
    from app.services.turno_service import reservar_turno

    # Create a temporary reservation for the patient so the slot is held
    try:
        turno_reservado = await reservar_turno(
            db,
            profesional_id=profesional_id,
            fecha=slot_fecha,
            hora_inicio=slot_hora,
            paciente_id=None,
        )
    except TurnoNoDisponibleError:
        logger.warning("Slot %s %s ya no disponible para lista de espera", slot_fecha, slot_hora)
        return None

    # Notify the patient
    await notificar_y_marcar(
        db,
        profesional_id=profesional_id,
        lista_espera_id=siguiente.id,
        turno_id=turno_reservado.id,
        chat_id=siguiente.telegram_chat_id,
    )

    return turno_reservado


async def procesar_timeouts_lista_espera(
    db: AsyncSession,
    profesional_id: int,
    minutos_timeout: int = 5,
) -> int:
    """Process expired waiting-list notifications and re-offer slots.

    Returns the number of expired records processed.
    """
    umbral = _utcnow_naive() - timedelta(minutes=minutos_timeout)
    result = await db.execute(
        select(ListaDeEspera).where(
            ListaDeEspera.profesional_id == profesional_id,
            ListaDeEspera.notificado == True,
            ListaDeEspera.notificado_en < umbral,
        )
    )
    vencidos = result.scalars().all()

    count = 0
    for registro in vencidos:
        # Re-query with lock to avoid races with user interactions
        result = await db.execute(
            select(ListaDeEspera)
            .where(
                ListaDeEspera.id == registro.id,
                ListaDeEspera.profesional_id == profesional_id,
            )
            .with_for_update()
        )
        locked = result.scalar_one_or_none()
        if locked is None:
            continue
        # Double-check still expired after locking
        if not (locked.notificado and locked.notificado_en and locked.notificado_en < umbral):
            continue

        turno_id = locked.turno_ofrecido_id
        fecha = locked.fecha_solicitada

        # Free the held turno if it is still a temporary reservation
        if turno_id is not None:
            result_turno = await db.execute(
                select(Turno)
                .where(Turno.id == turno_id, Turno.profesional_id == profesional_id)
                .with_for_update()
            )
            turno = result_turno.scalar_one_or_none()
            if turno is not None and turno.estado == "RESERVADO_TEMPORAL":
                turno.estado = "DISPONIBLE"
                turno.paciente_id = None
                await db.execute(
                    delete(ReservaTemporal).where(ReservaTemporal.turno_id == turno_id)
                )

        locked.notificado = False
        locked.turno_ofrecido_id = None
        locked.notificado_en = None
        locked.creado_en = _utcnow_naive()
        # Patrón A: el caller (scheduler) hace commit. No hacer commit aquí.
        count += 1

        # Re-evaluate queue for the same date
        await evaluar_lista_espera(db, profesional_id=profesional_id, fecha=fecha, turno_id=turno_id)

    return count
