"""Servicio de recordatorios (C-24).

Endpoint ``POST /api/v1/recordatorios/run`` consume ``run_recordatorios_para_todos``
para iterar profesionales activos y enviar recordatorios de los turnos CONFIRMADOS
cuya fecha cae en la ventana del ``fecha`` objetivo.

Patrón A: el service hace ``commit`` por profesional (después de procesar todos
sus turnos). Las funciones de ``notificacion_service`` (``obtener_turnos_para_recordar``,
``enviar_recordatorio_telegram``, ``marcar_recordatorio_enviado``) NO commitean
individualmente — solo modifican el estado en la sesión activa y este service
es responsable de persistir.

Try/except por profesional: un fallo de un profesional no aborta el batch —
se loguea y se continúa con el siguiente.
"""
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profesional import Profesional
from app.schemas.recordatorio import RecordatorioError, RecordatorioRunResponse
from app.services.notificacion_service import (
    enviar_recordatorio_telegram,
    marcar_recordatorio_enviado,
    obtener_turnos_para_recordar,
)

logger = logging.getLogger(__name__)


def _calcular_horas_antes(fecha: date) -> int:
    """Calcula la ventana de horas que cubre ``fecha`` desde ``ahora``.

    Heurística: ``(fecha - hoy).days * 24 + 12`` horas. El ``+12`` es un
    margen de cobertura para absorber drift de cron (mañana a las 10:00
    puede llegar al backend a las 10:05) sin perder slots tempranos del
    día objetivo.

    Si ``fecha < hoy`` retorna 0 (la ventana cubre solo el instante
    actual, lo cual excluye los turnos pasados por construcción en
    ``obtener_turnos_para_recordar``).
    """
    delta_dias = (fecha - date.today()).days
    return max(0, delta_dias * 24 + 12)


async def _procesar_profesional(
    db: AsyncSession,
    profesional: Profesional,
    horas_antes: int,
) -> tuple[int, int, list[RecordatorioError]]:
    """Procesa los turnos candidatos de UN profesional.

    Retorna (candidatos, enviados, errores) para que el caller agregue
    a los contadores globales. NO commitea — el caller hace el commit.
    """
    if not profesional.telegram_bot_token:
        logger.warning(
            f"Profesional {profesional.id} sin telegram_bot_token; "
            f"se saltea el envío de recordatorios."
        )
        return 0, 0, []

    turnos = await obtener_turnos_para_recordar(
        db,
        profesional_id=profesional.id,
        horas_antes=horas_antes,
    )

    bot_token = profesional.telegram_bot_token
    enviados = 0
    fallidos = 0
    errores: list[RecordatorioError] = []

    for turno in turnos:
        try:
            ok = await enviar_recordatorio_telegram(turno, bot_token=bot_token)
            if ok:
                await marcar_recordatorio_enviado(db, turno.id, profesional.id)
                enviados += 1
            else:
                fallidos += 1
                errores.append(
                    RecordatorioError(
                        profesional_id=profesional.id,
                        turno_id=turno.id,
                        mensaje="envío Telegram falló (reintento futuro)",
                    )
                )
        except Exception as exc:
            # Un turno individual no aborta al profesional — logueamos y seguimos.
            fallidos += 1
            errores.append(
                RecordatorioError(
                    profesional_id=profesional.id,
                    turno_id=turno.id,
                    mensaje=f"excepción enviando recordatorio: {type(exc).__name__}: {exc}",
                )
            )
            logger.error(
                f"Excepción enviando recordatorio turno {turno.id} "
                f"(profesional {profesional.id}): {exc}"
            )

    return len(turnos), enviados, errores


async def run_recordatorios_para_todos(
    db: AsyncSession,
    fecha: date,
) -> RecordatorioRunResponse:
    """Dispara recordatorios para todos los profesionales activos.

    Itera por ``Profesional where is_active=True``, obtiene los turnos
    candidatos con ``obtener_turnos_para_recordar`` y los envía. El
    contador ``total_candidatos`` refleja los turnos encontrados; el
    ``total_enviados`` los que se enviaron con éxito (o se marcaron
    como enviados sin envío por falta de destinatario); el
    ``total_fallidos`` los que requieren reintento futuro.

    Patrón A: ``commit`` por profesional para que un fallo en uno no
    descarte el trabajo de los demás. Try/except por profesional y por
    turno: un error no rompe el batch.
    """
    horas_antes = _calcular_horas_antes(fecha)
    logger.info(
        f"Run recordatorios: fecha={fecha.isoformat()}, horas_antes={horas_antes}"
    )

    result = await db.execute(
        select(Profesional).where(Profesional.is_active == True)
    )
    profesionales = result.scalars().all()

    total_candidatos = 0
    total_enviados = 0
    total_fallidos = 0
    errores: list[RecordatorioError] = []

    for profesional in profesionales:
        try:
            candidatos, enviados, errores_prof = await _procesar_profesional(
                db, profesional, horas_antes
            )
            # Patrón A: el service hace commit por profesional.
            await db.commit()
            total_candidatos += candidatos
            total_enviados += enviados
            total_fallidos += errores_prof.__len__()
            errores.extend(errores_prof)
            logger.info(
                f"Recordatorios profesional {profesional.id}: "
                f"{candidatos} candidatos, {enviados} enviados"
            )
        except Exception as exc:
            await db.rollback()
            total_fallidos += 1
            errores.append(
                RecordatorioError(
                    profesional_id=profesional.id,
                    turno_id=None,
                    mensaje=f"error procesando profesional: {type(exc).__name__}: {exc}",
                )
            )
            logger.exception(
                f"Error procesando recordatorios para profesional {profesional.id}: {exc}"
            )

    logger.info(
        f"Run recordatorios finalizado: {total_candidatos} candidatos, "
        f"{total_enviados} enviados, {total_fallidos} fallidos, "
        f"{len(errores)} errores"
    )

    return RecordatorioRunResponse(
        fecha=fecha,
        total_candidatos=total_candidatos,
        total_enviados=total_enviados,
        total_fallidos=total_fallidos,
        errores=errores,
    )
