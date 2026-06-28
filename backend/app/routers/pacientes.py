from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbDep, CurrentProfesionalDep
from app.models.paciente import Paciente
from app.schemas.paciente import PacienteCreate, PacienteRead, PacienteConHistorial, TurnoRead
from app.services.paciente_service import (
    crear_o_obtener_paciente,
    obtener_paciente_con_historial,
    listar_turnos_por_paciente,
)

router = APIRouter(prefix="/pacientes", tags=["pacientes"])


@router.post("", response_model=PacienteRead)
async def create_paciente(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    data: PacienteCreate,
    response: Response,
) -> PacienteRead:
    """Crea un paciente o retorna el existente si el DNI ya está registrado (auto-identificación).

    Patrón A + contrato unificado: el router SIEMPRE llama a
    ``crear_o_obtener_paciente`` (que usa savepoint y SELECT FOR UPDATE para
    resolver el race condition internamente). El router hace commit en happy
    path y rollback en error. El status code (200 vs 201) se decide según si
    el paciente fue creado o preexistía.
    """
    # Pre-check para status code: ¿existe ya? No es filtro de negocio (el
    # servicio es la fuente de verdad), solo nos permite mapear 200/201.
    pre_check = await db.execute(
        select(Paciente).where(
            Paciente.dni == data.dni,
            Paciente.profesional_id == profesional.id,
        )
    )
    preexisting = pre_check.scalar_one_or_none()
    if preexisting is not None:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED

    try:
        paciente = await crear_o_obtener_paciente(
            db, profesional_id=profesional.id, data=data
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="DNI duplicado"
        )
    return paciente


@router.get("/{paciente_id}", response_model=PacienteConHistorial)
async def get_paciente(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    paciente_id: int,
) -> PacienteConHistorial:
    """Obtiene un paciente por ID con su historial de turnos."""
    paciente = await obtener_paciente_con_historial(db, profesional_id=profesional.id, paciente_id=paciente_id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return paciente


@router.get("/{paciente_id}/turnos", response_model=list[TurnoRead])
async def get_paciente_turnos(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    paciente_id: int,
) -> list[TurnoRead]:
    """Lista todos los turnos asociados a un paciente."""
    # Verificar que el paciente existe antes de listar turnos
    paciente = await obtener_paciente_con_historial(db, profesional_id=profesional.id, paciente_id=paciente_id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return await listar_turnos_por_paciente(db, profesional_id=profesional.id, paciente_id=paciente_id)
