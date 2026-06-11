from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.exceptions import (
    TurnoNoDisponibleError,
    TurnoExpiradoError,
    PacienteConTurnoActivoError,
    TurnoNoEncontradoError,
    TurnoYaCanceladoError,
)


def turno_no_disponible_handler(request: Request, exc: TurnoNoDisponibleError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message},
    )


def turno_expirado_handler(request: Request, exc: TurnoExpiradoError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message},
    )


def paciente_con_turno_activo_handler(request: Request, exc: PacienteConTurnoActivoError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message},
    )


def turno_no_encontrado_handler(request: Request, exc: TurnoNoEncontradoError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message},
    )


def turno_ya_cancelado_handler(request: Request, exc: TurnoYaCanceladoError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message},
    )
