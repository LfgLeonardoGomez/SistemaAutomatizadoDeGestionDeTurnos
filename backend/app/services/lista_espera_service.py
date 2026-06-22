import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lista_de_espera import ListaDeEspera
from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from app.exceptions import TurnoNoEncontradoError, TurnoNoDisponibleError
from app.services.telegram_service import enviar_notificacion_lista_espera
from app.services.availability_service import calcular_disponibilidad
from app.config import Settings

logger = logging.getLogger(__name__)


async def registrar_en_lista_espera(
    db: AsyncSession,
    paciente_id: int,
    fecha_solicitada: date,
    telegram_chat_id: Optional[str] = None,
) -> ListaDeEspera:
    """Register a patient in the waiting list for a specific date."""
    result = await db.execute(select(Paciente).where(Paciente.id == paciente_id))
    paciente = result.scalar_one_or_none()
    if paciente is None:
        raise TurnoNoEncontradoError("Paciente no encontrado")

    registro = ListaDeEspera(
        paciente_id=paciente_id,
        fecha_solicitada=fecha_solicitada,
        telegram_chat_id=telegram_chat_id,
    )
    db.add(registro)
    await db.commit()
    await db.refresh(registro)
    return registro


async def eliminar_de_lista_espera(db: AsyncSession, lista_espera_id: int) -> None:
    """Remove a patient from the waiting list."""
    result = await db.execute(
        select(ListaDeEspera).where(ListaDeEspera.id == lista_espera_id)
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        raise TurnoNoEncontradoError("Registro de lista de espera no encontrado")

    await db.delete(registro)
    await db.commit()


async def obtener_siguiente_paciente_fifo(
    db: AsyncSession, fecha: date
) -> Optional[ListaDeEspera]:
    """Atomically select the next patient in FIFO order for a given date."""
    result = await db.execute(
        select(ListaDeEspera)
        .where(
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
    lista_espera_id: int,
    turno_id: int,
    chat_id: Optional[str],
) -> None:
    """Atomically mark the waiting-list record as notified and send Telegram message.

    If Telegram sending fails, the DB is NOT updated so the next evaluation
    will retry with the same patient.
    """
    result = await db.execute(
        select(ListaDeEspera).where(ListaDeEspera.id == lista_espera_id).with_for_update()
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        raise TurnoNoEncontradoError("Registro de lista de espera no encontrado")

    result_turno = await db.execute(select(Turno).where(Turno.id == turno_id))
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
        ok = await enviar_notificacion_lista_espera(chat_id, turno)
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
    registro.notificado_en = datetime.now()
    await db.commit()


async def aceptar_turno_lista_espera(
    db: AsyncSession, lista_espera_id: int
) -> Turno:
    """Accept the offered slot, confirm the turno, and remove from queue."""
    result = await db.execute(
        select(ListaDeEspera).where(ListaDeEspera.id == lista_espera_id).with_for_update()
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
        select(Turno).where(Turno.id == turno_ofrecido_id).with_for_update()
    )
    turno_ofrecido = result_turno.scalar_one_or_none()
    if turno_ofrecido is None:
        raise TurnoNoDisponibleError("El turno ofrecido ya no existe")

    # Lazy import to avoid circular dependency
    from app.services.turno_service import reservar_turno, confirmar_turno

    if turno_ofrecido.estado == "RESERVADO_TEMPORAL":
        # Directly confirm the existing temporary reservation
        paciente_data = {
            "nombre": paciente.nombre,
            "apellido": paciente.apellido,
            "dni": paciente.dni,
            "telefono": paciente.telefono,
        }
        confirmado = await confirmar_turno(db, turno_id=turno_ofrecido.id, paciente_data=paciente_data)
    else:
        # For cancelled (or any other non-reservable) turnos, create a new one
        nuevo_turno = await reservar_turno(
            db,
            fecha=turno_ofrecido.fecha,
            hora_inicio=turno_ofrecido.hora_inicio,
            paciente_id=paciente.id,
        )
        paciente_data = {
            "nombre": paciente.nombre,
            "apellido": paciente.apellido,
            "dni": paciente.dni,
            "telefono": paciente.telefono,
        }
        confirmado = await confirmar_turno(db, turno_id=nuevo_turno.id, paciente_data=paciente_data)

    # Remove from waiting list
    await db.delete(registro)
    await db.commit()
    await db.refresh(confirmado)
    return confirmado


async def rechazar_turno_lista_espera(
    db: AsyncSession, lista_espera_id: int, turno_id: int
) -> None:
    """Reject the offered slot, reset the record, and offer to next patient."""
    result = await db.execute(
        select(ListaDeEspera).where(ListaDeEspera.id == lista_espera_id).with_for_update()
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        raise TurnoNoEncontradoError("Registro de lista de espera no encontrado")

    # Free the offered turno if it is a temporary reservation
    result_turno = await db.execute(
        select(Turno).where(Turno.id == turno_id).with_for_update()
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
    registro.creado_en = datetime.now()
    await db.commit()

    await evaluar_lista_espera(db, fecha=fecha, turno_id=turno_id)


async def evaluar_lista_espera(
    db: AsyncSession,
    fecha: date,
    turno_id: Optional[int] = None,
) -> Optional[Turno]:
    """Evaluate the waiting list for a freed slot and notify the next patient.

    If *turno_id* is provided the slot info (fecha/hora) is read from that turno.
    Otherwise the first available slot on *fecha* is picked.
    """
    siguiente = await obtener_siguiente_paciente_fifo(db, fecha=fecha)
    if siguiente is None:
        logger.info("No hay pacientes en lista de espera para la fecha %s", fecha)
        return None

    # Determine which slot to reserve
    if turno_id is not None:
        result = await db.execute(select(Turno).where(Turno.id == turno_id))
        turno_origen = result.scalar_one_or_none()
        if turno_origen is None:
            logger.warning("Turno origen %s no encontrado; no se puede evaluar lista de espera", turno_id)
            return None
        slot_fecha = turno_origen.fecha
        slot_hora = turno_origen.hora_inicio
    else:
        # Pick first available slot on the date
        from app.models.profesional import Profesional
        result_prof = await db.execute(select(Profesional))
        profesional = result_prof.scalars().first()
        if profesional is None:
            return None
        disponibles = await calcular_disponibilidad(db, fecha, profesional.id)
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
        lista_espera_id=siguiente.id,
        turno_id=turno_reservado.id,
        chat_id=siguiente.telegram_chat_id,
    )

    return turno_reservado


async def procesar_timeouts_lista_espera(
    db: AsyncSession,
    minutos_timeout: int = 5,
) -> int:
    """Process expired waiting-list notifications and re-offer slots.

    Returns the number of expired records processed.
    """
    umbral = datetime.now() - timedelta(minutes=minutos_timeout)
    result = await db.execute(
        select(ListaDeEspera).where(
            ListaDeEspera.notificado == True,
            ListaDeEspera.notificado_en < umbral,
        )
    )
    vencidos = result.scalars().all()

    count = 0
    for registro in vencidos:
        # Re-query with lock to avoid races with user interactions
        result = await db.execute(
            select(ListaDeEspera).where(ListaDeEspera.id == registro.id).with_for_update()
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
                select(Turno).where(Turno.id == turno_id).with_for_update()
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
        locked.creado_en = datetime.now()
        await db.commit()
        count += 1

        # Re-evaluate queue for the same date
        await evaluar_lista_espera(db, fecha=fecha, turno_id=turno_id)

    return count
