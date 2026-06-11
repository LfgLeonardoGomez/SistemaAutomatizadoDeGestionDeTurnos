from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Response, status
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbDep
from app.schemas.turno import (
    ReservaTurnoRequest,
    ConfirmarTurnoRequest,
    TurnoResponse,
    SlotResponse,
)
from app.services.turno_service import (
    reservar_turno,
    confirmar_turno,
    consultar_disponibilidad,
)
from app.exceptions import (
    TurnoNoDisponibleError,
    TurnoExpiradoError,
    PacienteConTurnoActivoError,
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
