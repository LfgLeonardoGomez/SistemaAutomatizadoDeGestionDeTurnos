from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
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
    """Crea un paciente o retorna el existente si el DNI ya está registrado (auto-identificación)."""
    # Verificar si ya existe por DNI para este profesional
    result = await db.execute(
        select(Paciente).where(
            Paciente.dni == data.dni,
            Paciente.profesional_id == profesional.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        response.status_code = status.HTTP_200_OK
        return PacienteRead.model_validate(existing)

    response.status_code = status.HTTP_201_CREATED
    paciente = await crear_o_obtener_paciente(db, profesional_id=profesional.id, data=data)
    await db.commit()
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
