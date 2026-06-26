from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import timedelta
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, CurrentProfesionalDep, require_https
from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.turno import Turno
from app.schemas.profesional import (
    DisponibilidadResponse,
    ProfesionalConfigResponse,
    ProfesionalConfigUpdate,
    ProfesionalIntegracionesResponse,
    ProfesionalIntegracionesUpdate,
    ProfesionalMetricasResponse,
    ProfesionalTurnoHoyResponse,
)
from app.services.availability_service import calcular_disponibilidad

router = APIRouter(prefix="/profesional", tags=["profesional"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/configuracion", response_model=ProfesionalConfigResponse)
async def get_configuracion(
    profesional: CurrentProfesionalDep,
) -> ProfesionalConfigResponse:
    return ProfesionalConfigResponse.model_validate(profesional)


@router.put("/configuracion", response_model=ProfesionalConfigResponse)
async def update_configuracion(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    update: ProfesionalConfigUpdate,
) -> ProfesionalConfigResponse:
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


@router.put("/integraciones", response_model=ProfesionalIntegracionesResponse)
async def update_integraciones(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    update: ProfesionalIntegracionesUpdate,
    _https: None = Depends(require_https),
) -> ProfesionalIntegracionesResponse:
    if update.telegram_bot_token is not None:
        profesional.telegram_bot_token = update.telegram_bot_token
    if update.google_refresh_token is not None:
        profesional.google_refresh_token = update.google_refresh_token
    if update.google_calendar_id is not None:
        profesional.google_calendar_id = update.google_calendar_id

    await db.commit()
    await db.refresh(profesional)
    return ProfesionalIntegracionesResponse(
        has_telegram=bool(profesional.telegram_bot_token),
        has_google=bool(profesional.google_refresh_token),
        google_calendar_id=profesional.google_calendar_id or "primary",
    )


@router.get("/integraciones", response_model=ProfesionalIntegracionesResponse)
async def get_integraciones(
    profesional: CurrentProfesionalDep,
    _https: None = Depends(require_https),
) -> ProfesionalIntegracionesResponse:
    return ProfesionalIntegracionesResponse(
        has_telegram=bool(profesional.telegram_bot_token),
        has_google=bool(profesional.google_refresh_token),
        google_calendar_id=profesional.google_calendar_id or "primary",
    )


@router.get("/disponibilidad", response_model=DisponibilidadResponse)
async def get_disponibilidad(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    fecha: Annotated[date, Query(description="Fecha en formato YYYY-MM-DD")],
) -> DisponibilidadResponse:
    horarios = await calcular_disponibilidad(db, fecha, profesional.id)
    return DisponibilidadResponse(horarios=horarios)


@router.get("/turnos-hoy", response_model=list[ProfesionalTurnoHoyResponse])
async def get_turnos_hoy(
    db: DbDep,
    profesional: CurrentProfesionalDep,
) -> list[ProfesionalTurnoHoyResponse]:
    hoy = date.today()
    result = await db.execute(
        select(Turno)
        .where(
            Turno.fecha == hoy,
            Turno.estado == "CONFIRMADO",
            Turno.profesional_id == profesional.id,
        )
        .order_by(Turno.hora_inicio)
    )
    turnos = result.scalars().all()
    return [ProfesionalTurnoHoyResponse.model_validate(t) for t in turnos]


@router.get("/metricas", response_model=ProfesionalMetricasResponse)
async def get_metricas(
    db: DbDep,
    profesional: CurrentProfesionalDep,
) -> ProfesionalMetricasResponse:
    hoy = date.today()
    inicio_30d = hoy - timedelta(days=30)

    # turnos_hoy
    result_hoy = await db.execute(
        select(func.count()).where(
            and_(
                Turno.fecha == hoy,
                Turno.estado == "CONFIRMADO",
                Turno.profesional_id == profesional.id,
            )
        )
    )
    turnos_hoy = result_hoy.scalar_one() or 0

    # total created in last 30 days (any estado)
    result_total = await db.execute(
        select(func.count()).where(
            and_(
                Turno.fecha >= inicio_30d,
                Turno.fecha <= hoy,
                Turno.profesional_id == profesional.id,
            )
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
            and_(
                Turno.fecha >= inicio_30d,
                Turno.fecha <= hoy,
                Turno.estado == "CONFIRMADO",
                Turno.profesional_id == profesional.id,
            )
        )
    )
    confirmados_30d = result_conf.scalar_one() or 0

    # cancelled in last 30 days
    result_canc = await db.execute(
        select(func.count()).where(
            and_(
                Turno.fecha >= inicio_30d,
                Turno.fecha <= hoy,
                Turno.estado == "CANCELADO",
                Turno.profesional_id == profesional.id,
            )
        )
    )
    cancelados_30d = result_canc.scalar_one() or 0

    return ProfesionalMetricasResponse(
        turnos_hoy=turnos_hoy,
        tasa_confirmacion_30d=round(confirmados_30d / total_30d, 2),
        tasa_cancelacion_30d=round(cancelados_30d / total_30d, 2),
    )
