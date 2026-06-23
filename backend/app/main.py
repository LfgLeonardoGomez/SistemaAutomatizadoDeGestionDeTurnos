import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.dependencies import _get_sessionmaker
from app.scheduler.jobs import init_scheduler, shutdown_scheduler
from app.seed import seed_profesional

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    environment: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    app.state.settings = settings
    init_scheduler(app)
    # Seed default profesional on startup
    try:
        async_session = _get_sessionmaker()
        async with async_session() as session:
            await seed_profesional(session)
            await session.commit()
    except Exception as exc:
        logger.warning(f"Skipping seed on startup: {exc}")
    yield
    shutdown_scheduler(app)


app = FastAPI(
    title="Tesis N8N Turnos API",
    version="0.1.0",
    lifespan=lifespan,
)

from app.routers import pacientes
from app.routers.auth import router as auth_router
from app.routers.profesional import router as profesional_router
from app.routers.turnos import router as turnos_router
from app.routers.webhooks import router as webhooks_router
from app.routers.lista_espera import router as lista_espera_router
from app.exception_handlers import (
    turno_no_disponible_handler,
    turno_expirado_handler,
    paciente_con_turno_activo_handler,
    turno_no_encontrado_handler,
    turno_ya_cancelado_handler,
)
from app.exceptions import (
    TurnoNoDisponibleError,
    TurnoExpiradoError,
    PacienteConTurnoActivoError,
    TurnoNoEncontradoError,
    TurnoYaCanceladoError,
)

app.include_router(auth_router)
app.include_router(pacientes.router)
app.include_router(profesional_router)
app.include_router(turnos_router)
app.include_router(webhooks_router)
app.include_router(lista_espera_router)

app.add_exception_handler(TurnoNoDisponibleError, turno_no_disponible_handler)
app.add_exception_handler(TurnoExpiradoError, turno_expirado_handler)
app.add_exception_handler(PacienteConTurnoActivoError, paciente_con_turno_activo_handler)
app.add_exception_handler(TurnoNoEncontradoError, turno_no_encontrado_handler)
app.add_exception_handler(TurnoYaCanceladoError, turno_ya_cancelado_handler)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=Settings().env,
    )
