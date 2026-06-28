from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbDep, CurrentProfesionalDep
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
    confirmar_asistencia_turno,
    completar_turno,
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
    profesional: CurrentProfesionalDep,
    fecha: Annotated[date, Query(description="Fecha en formato YYYY-MM-DD")],
) -> list[SlotResponse]:
    """Retorna los slots disponibles para una fecha dada."""
    slots = await consultar_disponibilidad(db, profesional.id, fecha)
    return [SlotResponse(**s) for s in slots]


@router.post("", response_model=TurnoResponse, status_code=status.HTTP_201_CREATED)
async def create_turno(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    data: ReservaTurnoRequest,
    response: Response,
) -> TurnoResponse:
    """Crea una reserva temporal de turno. Patrón A: commit en happy path, rollback en except."""
    try:
        turno = await reservar_turno(
            db,
            profesional_id=profesional.id,
            fecha=data.fecha,
            hora_inicio=data.hora_inicio,
            paciente_id=data.paciente_id,
        )
        await db.commit()
    except PacienteConTurnoActivoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    except TurnoNoDisponibleError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return TurnoResponse.model_validate(turno)


@router.put("/{turno_id}/confirmar", response_model=TurnoResponse)
async def confirmar_turno_endpoint(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    turno_id: int,
    data: ConfirmarTurnoRequest,
) -> TurnoResponse:
    """Confirma un turno reservado temporalmente."""
    try:
        turno = await confirmar_turno(
            db,
            profesional_id=profesional.id,
            turno_id=turno_id,
            paciente_data=data.model_dump(),
        )
        await db.commit()
    except TurnoNoDisponibleError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except TurnoExpiradoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    except PacienteConTurnoActivoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return TurnoResponse.model_validate(turno)


@router.put("/{turno_id}/cancelar", response_model=TurnoResponse)
async def cancelar_turno_endpoint(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    turno_id: int,
) -> TurnoResponse:
    """Cancela un turno confirmado. Patrón A: commit en happy path, rollback en except."""
    try:
        turno = await cancelar_turno(db, profesional_id=profesional.id, turno_id=turno_id)
        await db.commit()
    except TurnoNoEncontradoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except TurnoYaCanceladoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return TurnoResponse.model_validate(turno)


@router.put("/{turno_id}/reprogramar", response_model=TurnoResponse)
async def reprogramar_turno_endpoint(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    turno_id: int,
    data: ReprogramarTurnoRequest,
) -> TurnoResponse:
    """Reprograma un turno confirmado a un nuevo slot.

    Patrón A: el servicio ejecuta las 3 sub-operaciones (cancelar, reservar,
    confirmar) sin commitear. El router es responsable del commit/rollback,
    garantizando atomicidad: si la confirmación del nuevo turno falla, la
    transacción completa se revierte y el turno original permanece CONFIRMADO.
    """
    try:
        paciente_data = data.paciente_data.model_dump() if data.paciente_data else None
        turno = await reprogramar_turno(
            db,
            profesional_id=profesional.id,
            turno_id=turno_id,
            nueva_fecha=data.nueva_fecha,
            nueva_hora_inicio=data.nueva_hora_inicio,
            paciente_data=paciente_data,
        )
        await db.commit()
    except TurnoNoEncontradoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except TurnoYaCanceladoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    except TurnoNoDisponibleError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    except PacienteConTurnoActivoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return TurnoResponse.model_validate(turno)


@router.put("/{turno_id}/completar", response_model=TurnoResponse)
async def completar_turno_endpoint(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    turno_id: int,
) -> TurnoResponse:
    """Marca un turno confirmado como completado.

    Wrapper delgado sobre ``turno_service.completar_turno`` (Patrón A).
    El router solo llama al servicio y maneja commit/rollback.
    """
    try:
        turno = await completar_turno(db, profesional_id=profesional.id, turno_id=turno_id)
        await db.commit()
    except TurnoNoEncontradoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except TurnoNoDisponibleError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return TurnoResponse.model_validate(turno)


@router.put("/{turno_id}/confirmar-asistencia", response_model=TurnoResponse)
async def confirmar_asistencia_endpoint(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    turno_id: int,
) -> TurnoResponse:
    """Confirma la asistencia de un turno ya confirmado (idempotente). Patrón A."""
    try:
        turno = await confirmar_asistencia_turno(db, profesional_id=profesional.id, turno_id=turno_id)
        await db.commit()
    except TurnoNoEncontradoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except TurnoYaCanceladoError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return TurnoResponse.model_validate(turno)
