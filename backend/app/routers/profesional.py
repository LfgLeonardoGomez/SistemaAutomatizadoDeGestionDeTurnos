from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.profesional import Profesional
from app.schemas.profesional import (
    DisponibilidadResponse,
    ProfesionalConfigResponse,
    ProfesionalConfigUpdate,
)
from app.services.availability_service import calcular_disponibilidad

# TODO: v1.0 asume single-profesional. Si el dominio evoluciona a multi-profesional,
# migrar a /profesionales/{id}/configuracion.
router = APIRouter(prefix="/profesional", tags=["profesional"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/configuracion", response_model=ProfesionalConfigResponse)
async def get_configuracion(db: DbDep) -> ProfesionalConfigResponse:
    result = await db.execute(select(Profesional))
    profesional = result.scalars().first()
    if not profesional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    return ProfesionalConfigResponse.model_validate(profesional)


@router.put("/configuracion", response_model=ProfesionalConfigResponse)
async def update_configuracion(
    db: DbDep,
    update: ProfesionalConfigUpdate,
) -> ProfesionalConfigResponse:
    result = await db.execute(select(Profesional))
    profesional = result.scalars().first()
    if not profesional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    if update.horario_inicio is not None:
        profesional.horario_inicio = update.horario_inicio
    if update.horario_fin is not None:
        profesional.horario_fin = update.horario_fin
    if update.dias_atencion is not None:
        profesional.dias_atencion = update.dias_atencion
    if update.duracion_turno is not None:
        profesional.duracion_turno = update.duracion_turno

    await db.commit()
    await db.refresh(profesional)
    return ProfesionalConfigResponse.model_validate(profesional)


@router.get("/disponibilidad", response_model=DisponibilidadResponse)
async def get_disponibilidad(
    db: DbDep,
    fecha: Annotated[date, Query(description="Fecha en formato YYYY-MM-DD")],
) -> DisponibilidadResponse:
    result = await db.execute(select(Profesional))
    profesional = result.scalars().first()
    if not profesional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    horarios = await calcular_disponibilidad(db, fecha, profesional.id)
    return DisponibilidadResponse(horarios=horarios)
