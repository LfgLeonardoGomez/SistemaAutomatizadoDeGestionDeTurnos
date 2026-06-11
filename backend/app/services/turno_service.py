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
    TurnoNoDisponibleError,
    TurnoExpiradoError,
    PacienteConTurnoActivoError,
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
    - Crea evento en Google Calendar (no bloquea la transacción; fallo logueado).
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
        await run_in_threadpool(calendar.create_event, turno)
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
