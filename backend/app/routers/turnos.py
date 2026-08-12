from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbDep, FlexibleProfesionalDep
from app.schemas.captura import (
    ActualizarCapturaRequest,
    CapturaPendienteResponse,
)
from app.schemas.turno import (
    ReservaTurnoRequest,
    ConfirmarTurnoRequest,
    ReprogramarTurnoRequest,
    TurnoResponse,
    TurnoActivoResponse,
    SlotResponse,
)
from app.services.captura_service import (
    actualizar_datos_captura,
    obtener_captura_pendiente,
    obtener_turnos_activos,
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
    CapturaNoEncontradaError,
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
    profesional: FlexibleProfesionalDep,
    fecha: Annotated[date, Query(description="Fecha en formato YYYY-MM-DD")],
) -> list[SlotResponse]:
    """Retorna los slots disponibles para una fecha dada."""
    slots = await consultar_disponibilidad(db, profesional.id, fecha)
    return [SlotResponse(**s) for s in slots]


@router.get("/activos", response_model=list[TurnoActivoResponse])
async def get_turnos_activos(
    db: DbDep,
    profesional: FlexibleProfesionalDep,
    telegram_chat_id: Annotated[
        str, Query(description="Chat de Telegram que consulta sus turnos")
    ],
) -> list[TurnoActivoResponse]:
    """Devuelve los turnos CONFIRMADOS y futuros que este chat puede gestionar.

    Declarada ANTES que cualquier ruta ``/{turno_id}/...`` a propósito: FastAPI
    matchea rutas en el orden en que se declaran, y si esta viniera después,
    ``activos`` se interpretaría como un ``turno_id`` (mismo motivo por el que
    ``/captura-pendiente`` está declarada arriba).
    """
    turnos = await obtener_turnos_activos(
        db, profesional_id=profesional.id, telegram_chat_id=telegram_chat_id
    )
    return [TurnoActivoResponse.model_validate(t) for t in turnos]


@router.get("/captura-pendiente", response_model=CapturaPendienteResponse)
async def get_captura_pendiente(
    db: DbDep,
    profesional: FlexibleProfesionalDep,
    telegram_chat_id: Annotated[
        str, Query(description="Chat de Telegram que respondió")
    ],
) -> CapturaPendienteResponse:
    """Devuelve la captura de datos pendiente para un chat de Telegram.

    C-27: cada mensaje del bot es una ejecución distinta de n8n, así que el
    orquestador no puede recordar que dejó una pregunta abierta. Consulta acá
    antes de interpretar un texto libre: un 200 significa "esto es la
    respuesta a mi pregunta", un 404 significa "tratalo como un mensaje
    normal". El 404 es un desenlace esperado, no un error.
    """
    captura = await obtener_captura_pendiente(
        db, profesional_id=profesional.id, telegram_chat_id=telegram_chat_id
    )
    if captura is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay una captura pendiente para este chat",
        )
    return CapturaPendienteResponse(
        turno_id=captura.turno_id, paso=captura.paso, datos=captura.datos
    )


@router.patch("/{turno_id}/captura", response_model=CapturaPendienteResponse)
async def actualizar_captura_endpoint(
    db: DbDep,
    profesional: FlexibleProfesionalDep,
    turno_id: int,
    data: ActualizarCapturaRequest,
) -> CapturaPendienteResponse:
    """Guarda una respuesta de la conversación y devuelve el paso siguiente.

    Mergea sobre lo ya capturado: cada mensaje trae una sola respuesta y no
    debe pisar las anteriores.
    """
    try:
        captura = await actualizar_datos_captura(
            db,
            profesional_id=profesional.id,
            turno_id=turno_id,
            nuevos_datos=data.datos,
        )
        await db.commit()
    except CapturaNoEncontradaError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    return CapturaPendienteResponse(
        turno_id=captura.turno_id, paso=captura.paso, datos=captura.datos
    )


@router.post("", response_model=TurnoResponse, status_code=status.HTTP_201_CREATED)
async def create_turno(
    db: DbDep,
    profesional: FlexibleProfesionalDep,
    data: ReservaTurnoRequest,
    response: Response,
) -> TurnoResponse:
    """Crea una reserva temporal de turno. Patrón A: commit en happy path, rollback en except.

    C-23 TAREA 6: si el request trae ``telegram_chat_id``, se propaga al
    servicio para registrar un ``TurnoDestinatario`` canal=TELEGRAM. Si no
    viene, el turno queda sin destinatario (reserva válida, recordatorio
    no se envía).
    """
    try:
        turno = await reservar_turno(
            db,
            profesional_id=profesional.id,
            fecha=data.fecha,
            hora_inicio=data.hora_inicio,
            paciente_id=data.paciente_id,
            telegram_chat_id=data.telegram_chat_id,
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
    profesional: FlexibleProfesionalDep,
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
    profesional: FlexibleProfesionalDep,
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
    profesional: FlexibleProfesionalDep,
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
    profesional: FlexibleProfesionalDep,
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
    profesional: FlexibleProfesionalDep,
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
