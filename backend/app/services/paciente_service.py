from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.models.paciente import Paciente
from app.models.turno import Turno
from app.schemas.paciente import PacienteCreate, PacienteRead, PacienteConHistorial, TurnoRead


async def crear_o_obtener_paciente(
    db_session, profesional_id: int, data: PacienteCreate
) -> PacienteRead:
    """Crea un paciente si no existe; si el DNI ya existe para ese profesional, retorna el existente.

    Uses a savepoint (begin_nested) for IntegrityError handling so the caller's
    transaction is NOT destroyed. The caller is responsible for committing.
    """
    # Buscar con SELECT FOR UPDATE para prevenir race conditions
    stmt = (
        select(Paciente)
        .where(Paciente.profesional_id == profesional_id, Paciente.dni == data.dni)
        .with_for_update()
    )
    result = await db_session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        return PacienteRead.model_validate(existing)

    paciente = Paciente(
        nombre=data.nombre,
        apellido=data.apellido,
        dni=data.dni,
        telefono=data.telefono,
        profesional_id=profesional_id,
    )
    db_session.add(paciente)
    try:
        # Use savepoint so IntegrityError doesn't destroy the outer transaction
        async with db_session.begin_nested():
            await db_session.flush()
        await db_session.refresh(paciente)
    except IntegrityError:
        # Fallback: otro proceso creó el paciente entre el SELECT y el INSERT
        db_session.expunge(paciente)
        result = await db_session.execute(
            select(Paciente).where(
                Paciente.profesional_id == profesional_id, Paciente.dni == data.dni
            )
        )
        existing = result.scalar_one()
        return PacienteRead.model_validate(existing)

    return PacienteRead.model_validate(paciente)


async def listar_pacientes(
    db_session, profesional_id: int, limit: int = 50, offset: int = 0
) -> list[PacienteRead]:
    """Lista los pacientes de un profesional, ordenados por apellido y nombre.

    Tenant-scoped: solo devuelve pacientes del ``profesional_id`` dado.
    Paginado con ``limit``/``offset`` para acotar datasets grandes.
    """
    stmt = (
        select(Paciente)
        .where(Paciente.profesional_id == profesional_id)
        .order_by(Paciente.apellido, Paciente.nombre)
        .limit(limit)
        .offset(offset)
    )
    result = await db_session.execute(stmt)
    pacientes = result.scalars().all()
    return [PacienteRead.model_validate(p) for p in pacientes]


async def obtener_paciente_con_historial(
    db_session, profesional_id: int, paciente_id: int
) -> Optional[PacienteConHistorial]:
    """Obtiene paciente con su historial de turnos usando joinedload."""
    stmt = (
        select(Paciente)
        .where(Paciente.id == paciente_id, Paciente.profesional_id == profesional_id)
        .options(joinedload(Paciente.turnos))
    )
    result = await db_session.execute(stmt)
    paciente = result.unique().scalar_one_or_none()

    if paciente is None:
        return None

    return PacienteConHistorial.model_validate(paciente)


async def listar_turnos_por_paciente(
    db_session, profesional_id: int, paciente_id: int
) -> list[TurnoRead]:
    """Lista todos los turnos asociados a un paciente para un profesional dado."""
    stmt = select(Turno).where(
        Turno.paciente_id == paciente_id, Turno.profesional_id == profesional_id
    )
    result = await db_session.execute(stmt)
    turnos = result.scalars().all()
    return [TurnoRead.model_validate(t) for t in turnos]
