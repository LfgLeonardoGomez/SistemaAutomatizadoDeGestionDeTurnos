from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Response, status
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbDep
from app.schemas.turno import (
    ReservaTurnoRequest,
    ConfirmarTurnoRequest,
    ReprogramarTurnoRequest,
    TurnoResponse,
    SlotResponse,
)
from app.services.turno_service import (
    reservar_turno,
    confirmar_turno,
    cancelar_turno,
    reprogramar_turno,
    consultar_disponibilidad,
    marcar_turnos_completados,
)
from app.exceptions import (
    TurnoNoDisponibleError,
    TurnoExpiradoError,
    PacienteConTurnoActivoError,
    TurnoNoEncontradoError,
    TurnoYaCanceladoError,
)

router = APIRouter(prefix="/turnos", tags=["turnos"])


@router.get("/disponibles", response_model=list[SlotResponse])
async def get_turnos_disponibles(
    db: DbDep,
    fecha: Annotated[date, Query(description="Fecha en formato YYYY-MM-DD")],
) -> list[SlotResponse]:
    """Retorna los slots disponibles para una fecha dada."""
    slots = await consultar_disponibilidad(db, fecha)
    return [SlotResponse(**s) for s in slots]


@router.post("", response_model=TurnoResponse, status_code=status.HTTP_201_CREATED)
async def create_turno(
    db: DbDep,
    data: ReservaTurnoRequest,
    response: Response,
) -> TurnoResponse:
    """Crea una reserva temporal de turno."""
    try:
        turno = await reservar_turno(
            db,
            fecha=data.fecha,
            hora_inicio=data.hora_inicio,
            paciente_id=data.paciente_id,
        )
    except PacienteConTurnoActivoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    except TurnoNoDisponibleError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return TurnoResponse.model_validate(turno)


@router.put("/{turno_id}/confirmar", response_model=TurnoResponse)
async def confirmar_turno_endpoint(
    db: DbDep,
    turno_id: int,
    data: ConfirmarTurnoRequest,
) -> TurnoResponse:
    """Confirma un turno reservado temporalmente."""
    try:
        turno = await confirmar_turno(
            db,
            turno_id=turno_id,
            paciente_data=data.model_dump(),
        )
    except TurnoNoDisponibleError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except TurnoExpiradoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    except PacienteConTurnoActivoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return TurnoResponse.model_validate(turno)


@router.put("/{turno_id}/cancelar", response_model=TurnoResponse)
async def cancelar_turno_endpoint(
    db: DbDep,
    turno_id: int,
) -> TurnoResponse:
    """Cancela un turno confirmado."""
    try:
        turno = await cancelar_turno(db, turno_id=turno_id)
    except TurnoNoEncontradoError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except TurnoYaCanceladoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return TurnoResponse.model_validate(turno)


@router.put("/{turno_id}/reprogramar", response_model=TurnoResponse)
async def reprogramar_turno_endpoint(
    db: DbDep,
    turno_id: int,
    data: ReprogramarTurnoRequest,
) -> TurnoResponse:
    """Reprograma un turno confirmado a un nuevo slot."""
    try:
        paciente_data = data.paciente_data.model_dump() if data.paciente_data else None
        turno = await reprogramar_turno(
            db,
            turno_id=turno_id,
            nueva_fecha=data.nueva_fecha,
            nueva_hora_inicio=data.nueva_hora_inicio,
            paciente_data=paciente_data,
        )
    except TurnoNoEncontradoError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except TurnoYaCanceladoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    except TurnoNoDisponibleError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    except PacienteConTurnoActivoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return TurnoResponse.model_validate(turno)


@router.put("/{turno_id}/completar", response_model=TurnoResponse)
async def completar_turno_endpoint(
    db: DbDep,
    turno_id: int,
) -> TurnoResponse:
    """Marca un turno confirmado como completado."""
    from sqlalchemy import select
    from app.models.turno import Turno

    result = await db.execute(
        select(Turno).where(Turno.id == turno_id).with_for_update()
    )
    turno = result.scalar_one_or_none()
    if turno is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")
    if turno.estado == "COMPLETADO":
        return TurnoResponse.model_validate(turno)
    if turno.estado != "CONFIRMADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El turno no puede ser completado porque no está confirmado",
        )
    turno.estado = "COMPLETADO"
    await db.commit()
    await db.refresh(turno)
    return TurnoResponse.model_validate(turno)
