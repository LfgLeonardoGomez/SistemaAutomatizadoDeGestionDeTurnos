from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import timedelta
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.turno import Turno
from app.schemas.profesional import (
    DisponibilidadResponse,
    ProfesionalConfigResponse,
    ProfesionalConfigUpdate,
    ProfesionalMetricasResponse,
    ProfesionalTurnoHoyResponse,
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


@router.get("/turnos-hoy", response_model=list[ProfesionalTurnoHoyResponse])
async def get_turnos_hoy(db: DbDep) -> list[ProfesionalTurnoHoyResponse]:
    hoy = date.today()
    result = await db.execute(
        select(Turno)
        .where(Turno.fecha == hoy, Turno.estado == "CONFIRMADO")
        .order_by(Turno.hora_inicio)
    )
    turnos = result.scalars().all()
    return [ProfesionalTurnoHoyResponse.model_validate(t) for t in turnos]


@router.get("/metricas", response_model=ProfesionalMetricasResponse)
async def get_metricas(db: DbDep) -> ProfesionalMetricasResponse:
    hoy = date.today()
    inicio_30d = hoy - timedelta(days=30)

    # turnos_hoy
    result_hoy = await db.execute(
        select(func.count()).where(
            and_(Turno.fecha == hoy, Turno.estado == "CONFIRMADO")
        )
    )
    turnos_hoy = result_hoy.scalar_one() or 0

    # total created in last 30 days (any estado)
    result_total = await db.execute(
        select(func.count()).where(
            and_(Turno.fecha >= inicio_30d, Turno.fecha <= hoy)
        )
    )
    total_30d = result_total.scalar_one() or 0

    if total_30d == 0:
        return ProfesionalMetricasResponse(
            turnos_hoy=turnos_hoy,
            tasa_confirmacion_30d=0.0,
            tasa_cancelacion_30d=0.0,
        )

    # confirmed in last 30 days
    result_conf = await db.execute(
        select(func.count()).where(
            and_(Turno.fecha >= inicio_30d, Turno.fecha <= hoy, Turno.estado == "CONFIRMADO")
        )
    )
    confirmados_30d = result_conf.scalar_one() or 0

    # cancelled in last 30 days
    result_canc = await db.execute(
        select(func.count()).where(
            and_(Turno.fecha >= inicio_30d, Turno.fecha <= hoy, Turno.estado == "CANCELADO")
        )
    )
    cancelados_30d = result_canc.scalar_one() or 0

    return ProfesionalMetricasResponse(
        turnos_hoy=turnos_hoy,
        tasa_confirmacion_30d=round(confirmados_30d / total_30d, 2),
        tasa_cancelacion_30d=round(cancelados_30d / total_30d, 2),
    )
