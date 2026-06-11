import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import _get_sessionmaker
from app.services.turno_service import liberar_reservas_vencidas

logger = logging.getLogger(__name__)


async def _liberar_reservas_vencidas_job(session: Optional[AsyncSession] = None) -> None:
    """Job periódico: libera reservas temporales vencidas."""
    try:
        if session is None:
            async_session = _get_sessionmaker()
            async with async_session() as sess:
                liberados = await liberar_reservas_vencidas(sess)
        else:
            liberados = await liberar_reservas_vencidas(session)
        logger.info(f"Job liberar_reservas_vencidas completado: {liberados} liberados")
    except Exception as exc:
        logger.exception(f"Error en job liberar_reservas_vencidas: {exc}")


def init_scheduler(app: FastAPI) -> None:
    scheduler = AsyncIOScheduler()
    scheduler.start()
    app.state.scheduler = scheduler

    # Job de limpieza de reservas temporales vencidas — cada 1 minuto
    scheduler.add_job(
        _liberar_reservas_vencidas_job,
        "interval",
        id="liberar_reservas_vencidas",
        minutes=1,
        replace_existing=True,
    )
    logger.info("Job liberar_reservas_vencidas registrado (intervalo 1 minuto)")

    # Dummy job para verificar que el scheduler acepta registros
    @scheduler.scheduled_job("interval", id="dummy_job", seconds=3600)
    def dummy_job() -> None:
        pass


def shutdown_scheduler(app: FastAPI) -> None:
    scheduler: AsyncIOScheduler | None = getattr(app.state, "scheduler", None)
    if scheduler:
        scheduler.shutdown(wait=False)
