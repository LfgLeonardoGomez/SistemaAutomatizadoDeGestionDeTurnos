import logging
from datetime import date, time, datetime, timedelta
from typing import Optional, Any

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.concurrency import run_in_threadpool

from app.config import Settings
from app.models.profesional import Profesional
from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from app.services.availability_service import calcular_disponibilidad
from app.services.paciente_service import crear_o_obtener_paciente
from app.services.calendar_service import CalendarService
from app.schemas.paciente import PacienteCreate
from app.exceptions import (
    TurnoError,
    TurnoNoDisponibleError,
    TurnoExpiradoError,
    PacienteConTurnoActivoError,
    TurnoNoEncontradoError,
    TurnoYaCanceladoError,
)

logger = logging.getLogger(__name__)


async def _get_profesional_default(db: AsyncSession) -> Optional[Profesional]:
    result = await db.execute(select(Profesional))
    return result.scalars().first()


async def _paciente_tiene_turno_activo(
    db: AsyncSession, paciente_id: int, exclude_turno_id: Optional[int] = None
) -> bool:
    """RN-TU-01: verifica si el paciente tiene un turno en RESERVADO_TEMPORAL o CONFIRMADO."""
    if paciente_id is None:
        return False
    stmt = (
        select(Turno)
        .where(
            Turno.paciente_id == paciente_id,
            Turno.estado.in_(["RESERVADO_TEMPORAL", "CONFIRMADO"]),
        )
        .with_for_update()
    )
    if exclude_turno_id is not None:
        stmt = stmt.where(Turno.id != exclude_turno_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def reservar_turno(
    db: AsyncSession,
    fecha: date,
    hora_inicio: time,
    paciente_id: Optional[int] = None,
    profesional_id: Optional[int] = None,
    settings: Optional[Settings] = None,
) -> Turno:
    """
    Reserva un turno temporalmente.

    - Valida RN-TU-01: paciente sin turno activo.
    - Bloquea turnos de la fecha para evitar carreras.
    - Crea Turno en RESERVADO_TEMPORAL + ReservaTemporal.
    """
    if paciente_id is not None:
        if await _paciente_tiene_turno_activo(db, paciente_id):
            raise PacienteConTurnoActivoError()

    profesional = await _get_profesional_default(db)
    if profesional is None:
        raise TurnoNoDisponibleError("No hay profesional configurado")

    target_id = profesional_id or profesional.id

    # Bloquear todas las filas de turno de la fecha para serializar reservas concurrentes.
    await db.execute(
        select(Turno)
        .where(Turno.fecha == fecha, Turno.profesional_id == target_id)
        .with_for_update()
    )

    # Verificar disponibilidad dentro de la transacción bloqueada
    disponibles = await calcular_disponibilidad(db, fecha, target_id)
    slot_str = hora_inicio.strftime("%H:%M")
    if slot_str not in disponibles:
        raise TurnoNoDisponibleError()

    duracion = profesional.duracion_turno
    inicio_min = hora_inicio.hour * 60 + hora_inicio.minute
    fin_min = inicio_min + duracion
    hora_fin = time(fin_min // 60, fin_min % 60)

    turno = Turno(
        fecha=fecha,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        estado="RESERVADO_TEMPORAL",
        profesional_id=target_id,
        paciente_id=paciente_id,
    )
    db.add(turno)
    await db.flush()

    cfg = settings or Settings()
    expiracion = datetime.now() + timedelta(minutes=cfg.reserva_temporal_minutos)
    reserva = ReservaTemporal(turno_id=turno.id, expiracion=expiracion)
    db.add(reserva)
    await db.commit()
    await db.refresh(turno)
    return turno


async def confirmar_turno(
    db: AsyncSession,
    turno_id: int,
    paciente_data: dict[str, Any],
) -> Turno:
    """
    Confirma un turno reservado temporalmente.

    - Valida que el turno esté RESERVADO_TEMPORAL y no haya expirado.
    - Valida RN-TU-01 atómicamente (SELECT FOR UPDATE sobre turnos del paciente).
    - Registra/identifica al paciente.
    - Actualiza turno a CONFIRMADO, elimina ReservaTemporal.
    - Crea evento en Google Calendar y persiste el `google_event_id` retornado.
      Si Calendar falla, el turno sigue CONFIRMADO y `google_event_id` queda NULL;
      no se revierte la confirmación porque la DB es la fuente de verdad.
    """
    # Bloquear el turno a confirmar
    result = await db.execute(
        select(Turno).where(Turno.id == turno_id).with_for_update()
    )
    turno = result.scalar_one_or_none()
    if turno is None:
        raise TurnoNoDisponibleError("Turno no encontrado")
    if turno.estado != "RESERVADO_TEMPORAL":
        raise TurnoExpiradoError("El turno no está en estado RESERVADO_TEMPORAL")

    # Verificar que la ReservaTemporal sigue existiendo
    result = await db.execute(
        select(ReservaTemporal).where(ReservaTemporal.turno_id == turno_id)
    )
    reserva = result.scalar_one_or_none()
    if reserva is None:
        raise TurnoExpiradoError("La reserva temporal ya no existe")
    if reserva.expiracion < datetime.now():
        raise TurnoExpiradoError("La reserva temporal ha expirado")

    # Identificar/crear paciente
    paciente_schema = PacienteCreate(
        nombre=paciente_data["nombre"],
        apellido=paciente_data["apellido"],
        dni=paciente_data["dni"],
        telefono=paciente_data["telefono"],
    )
    paciente_read = await crear_o_obtener_paciente(db, paciente_schema)
    paciente_id = paciente_read.id

    # RN-TU-01: validar que no tenga otro turno activo (excluyendo el actual)
    if await _paciente_tiene_turno_activo(db, paciente_id, exclude_turno_id=turno.id):
        raise PacienteConTurnoActivoError()

    # Confirmar turno
    turno.estado = "CONFIRMADO"
    turno.paciente_id = paciente_id

    # Eliminar ReservaTemporal
    await db.execute(
        delete(ReservaTemporal).where(ReservaTemporal.turno_id == turno_id)
    )

    await db.commit()
    await db.refresh(turno)

    # Crear evento en Google Calendar (no bloquea el event loop)
    try:
        # Forzar refresh de relaciones para que CalendarService tenga datos completos
        await db.refresh(turno, attribute_names=["paciente", "profesional"])
        calendar = CalendarService()
        event_id = await run_in_threadpool(calendar.create_event, turno)
        turno.google_event_id = event_id
        await db.commit()
        await db.refresh(turno)
    except Exception as exc:
        logger.error(f"Fallo al crear evento en Calendar para turno {turno.id}: {exc}")
        # No revertimos la confirmación; el turno es la fuente de verdad

    return turno


async def liberar_reservas_vencidas(db: AsyncSession) -> int:
    """
    Libera reservas temporales cuya expiración haya pasado.

    Retorna la cantidad de reservas liberadas.
    """
    result = await db.execute(
        select(ReservaTemporal).where(ReservaTemporal.expiracion < datetime.now())
    )
    vencidas = result.scalars().all()

    count = 0
    for reserva in vencidas:
        result = await db.execute(
            select(Turno).where(Turno.id == reserva.turno_id).with_for_update()
        )
        turno = result.scalar_one_or_none()
        if turno is not None:
            turno.estado = "DISPONIBLE"
            turno.paciente_id = None
        await db.delete(reserva)
        count += 1

    if count:
        logger.info(f"Liberadas {count} reservas temporales vencidas")
        await db.commit()
    else:
        logger.debug("No hay reservas temporales vencidas para liberar")

    return count


async def marcar_turnos_completados(db: AsyncSession) -> int:
    """
    Marca turnos CONFIRMADOS cuya fecha y hora de fin ya pasaron como COMPLETADOS.

    Ejecutado periódicamente por el scheduler (default cada 5 minutos).
    Usa SELECT FOR UPDATE para evitar race conditions con cancelaciones
    o completados manuales concurrentes.
    Retorna la cantidad de turnos actualizados.
    """
    result = await db.execute(
        select(Turno)
        .where(Turno.estado == "CONFIRMADO")
        .with_for_update()
    )
    turnos = result.scalars().all()

    ahora = datetime.now()
    count = 0
    for turno in turnos:
        fin_turno = datetime.combine(turno.fecha, turno.hora_fin)
        if fin_turno < ahora:
            turno.estado = "COMPLETADO"
            count += 1

    if count:
        logger.info(f"Marcados {count} turnos como COMPLETADO")
        await db.commit()
    else:
        logger.debug("No hay turnos para marcar como COMPLETADO")

    return count


async def cancelar_turno(db: AsyncSession, turno_id: int) -> Turno:
    """
    Cancela un turno confirmado.

    - Bloquea la fila con SELECT FOR UPDATE.
    - Valida que el turno exista y esté CONFIRMADO.
    - Actualiza estado a CANCELADO y hace COMMIT.
    - Lee `google_event_id` desde la columna persistente del modelo Turno.
      Si existe, elimina el evento de Google Calendar en best-effort;
      si falla o es NULL, no se revierte la cancelación (DB es fuente de verdad).
    """
    result = await db.execute(
        select(Turno).where(Turno.id == turno_id).with_for_update()
    )
    turno = result.scalar_one_or_none()
    if turno is None:
        raise TurnoNoEncontradoError()
    if turno.estado == "CANCELADO":
        raise TurnoYaCanceladoError()
    if turno.estado != "CONFIRMADO":
        raise TurnoYaCanceladoError("El turno no puede ser cancelado porque no está confirmado")

    turno.estado = "CANCELADO"
    await db.commit()
    await db.refresh(turno)

    # Eliminar evento de Google Calendar (best-effort, no bloquea)
    google_event_id = turno.google_event_id
    if google_event_id:
        try:
            calendar = CalendarService()
            await run_in_threadpool(calendar.delete_event, google_event_id)
        except Exception as exc:
            logger.error(f"Fallo al eliminar evento de Calendar para turno {turno.id}: {exc}")
            # No revertimos la cancelación; DB es fuente de verdad

    return turno


async def reprogramar_turno(
    db: AsyncSession,
    turno_id: int,
    nueva_fecha: date,
    nueva_hora_inicio: time,
    paciente_data: Optional[dict[str, Any]] = None,
    settings: Optional[Settings] = None,
) -> Turno:
    """
    Reprograma un turno confirmado.

    - Cancela el turno anterior vía `cancelar_turno()`, que lee `google_event_id`
      desde la columna persistente y elimina el evento viejo de Calendar en
      best-effort.
    - Reserva un nuevo slot con `reservar_turno()`.
    - Confirma el nuevo turno con `confirmar_turno()`, que persiste el nuevo
      `google_event_id` retornado por CalendarService.
    - Si alguna operación de Calendar falla, se loguea pero no se revierte;
      la DB es la fuente de verdad.
    - Retorna el nuevo turno CONFIRMADO.
    """
    result = await db.execute(
        select(Turno).where(Turno.id == turno_id).with_for_update()
    )
    turno_viejo = result.scalar_one_or_none()
    if turno_viejo is None:
        raise TurnoNoEncontradoError()
    if turno_viejo.estado == "CANCELADO":
        raise TurnoYaCanceladoError()
    if turno_viejo.estado != "CONFIRMADO":
        raise TurnoYaCanceladoError("El turno no puede ser reprogramado porque no está confirmado")

    # Reutilizar datos del paciente si no se proporcionan
    if paciente_data is None:
        if turno_viejo.paciente_id is None:
            raise TurnoError("El turno no tiene paciente asociado")
        result = await db.execute(
            select(Paciente).where(Paciente.id == turno_viejo.paciente_id)
        )
        paciente = result.scalar_one_or_none()
        if paciente is None:
            raise TurnoError("Paciente no encontrado")
        paciente_data = {
            "nombre": paciente.nombre,
            "apellido": paciente.apellido,
            "dni": paciente.dni,
            "telefono": paciente.telefono,
        }

    # Cancelar turno anterior (libera slot y elimina calendar event best-effort)
    await cancelar_turno(db, turno_viejo.id)

    # Reservar nuevo slot
    nuevo_turno = await reservar_turno(
        db,
        fecha=nueva_fecha,
        hora_inicio=nueva_hora_inicio,
        paciente_id=turno_viejo.paciente_id,
        settings=settings,
    )

    # Confirmar nuevo turno
    confirmado = await confirmar_turno(
        db,
        turno_id=nuevo_turno.id,
        paciente_data=paciente_data,
    )

    return confirmado


async def consultar_disponibilidad(
    db: AsyncSession,
    fecha: date,
    profesional_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """
    Retorna los slots libres para una fecha como lista de diccionarios.
    """
    profesional = await _get_profesional_default(db)
    if profesional is None:
        return []

    target_id = profesional_id or profesional.id
    horarios = await calcular_disponibilidad(db, fecha, target_id)

    slots = []
    for h_str in horarios:
        h = time.fromisoformat(h_str)
        inicio_min = h.hour * 60 + h.minute
        fin_min = inicio_min + profesional.duracion_turno
        hora_fin = f"{fin_min // 60:02d}:{fin_min % 60:02d}"
        slots.append({
            "hora_inicio": h_str,
            "hora_fin": hora_fin,
            "disponible": True,
        })
    return slots
