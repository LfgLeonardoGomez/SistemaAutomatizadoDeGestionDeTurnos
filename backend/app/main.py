from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI
from pydantic import BaseModel

from app.config import Settings
from app.scheduler.jobs import init_scheduler, shutdown_scheduler


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
    yield
    shutdown_scheduler(app)


app = FastAPI(
    title="Tesis N8N Turnos API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=Settings().env,
    )
