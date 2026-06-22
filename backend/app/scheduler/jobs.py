import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import _get_sessionmaker
from app.services.turno_service import liberar_reservas_vencidas, marcar_turnos_completados
from app.services.lista_espera_service import procesar_timeouts_lista_espera
from app.config import Settings

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


async def _marcar_turnos_completados_job(session: Optional[AsyncSession] = None) -> None:
    """Job periódico: marca turnos confirmados pasados como completados."""
    try:
        if session is None:
            async_session = _get_sessionmaker()
            async with async_session() as sess:
                actualizados = await marcar_turnos_completados(sess)
        else:
            actualizados = await marcar_turnos_completados(session)
        logger.info(f"Job marcar_turnos_completados completado: {actualizados} actualizados")
    except Exception as exc:
        logger.exception(f"Error en job marcar_turnos_completados: {exc}")


async def _procesar_timeouts_lista_espera_job(session: Optional[AsyncSession] = None) -> None:
    """Job periódico: procesa timeouts de lista de espera."""
    try:
        settings = Settings()
        minutos = settings.lista_espera_minutos
        if session is None:
            async_session = _get_sessionmaker()
            async with async_session() as sess:
                procesados = await procesar_timeouts_lista_espera(sess, minutos_timeout=minutos)
        else:
            procesados = await procesar_timeouts_lista_espera(session, minutos_timeout=minutos)
        logger.info(f"Job procesar_timeouts_lista_espera completado: {procesados} procesados")
    except Exception as exc:
        logger.exception(f"Error en job procesar_timeouts_lista_espera: {exc}")


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

    # Job de transición a COMPLETADO — cada 5 minutos por defecto
    scheduler.add_job(
        _marcar_turnos_completados_job,
        "interval",
        id="marcar_turnos_completados",
        minutes=app.state.settings.completado_job_interval_minutos if hasattr(app.state, "settings") else 5,
        replace_existing=True,
    )
    logger.info("Job marcar_turnos_completados registrado (intervalo 5 minutos)")

    # Job de timeout de lista de espera — cada 1 minuto
    scheduler.add_job(
        _procesar_timeouts_lista_espera_job,
        "interval",
        id="procesar_timeouts_lista_espera",
        minutes=1,
        replace_existing=True,
    )
    logger.info("Job procesar_timeouts_lista_espera registrado (intervalo 1 minuto)")


def shutdown_scheduler(app: FastAPI) -> None:
    scheduler: AsyncIOScheduler | None = getattr(app.state, "scheduler", None)
    if scheduler:
        scheduler.shutdown(wait=False)
