"""Router de recordatorios (C-24).

Expone ``POST /api/v1/recordatorios/run`` consumido por el workflow
n8n ``flujo-recordatorio.json`` (cron diario). El endpoint autentica
con ``X-API-Key`` (cualquier api_key válida de un profesional activo)
y dispara el envío de recordatorios para TODOS los profesionales
activos, no solo el que autenticó.

Decisión 8 del design: el endpoint se autentica con cualquier
``X-API-Key`` válida, pero itera sobre todos los profesionales
activos — el caller es solo el invocador, no el destinatario.
"""
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbDep, get_profesional_by_api_key
from app.models.profesional import Profesional
from app.schemas.recordatorio import RecordatorioRunResponse
from app.services.recordatorio_service import run_recordatorios_para_todos

router = APIRouter(prefix="/api/v1/recordatorios", tags=["recordatorios"])


@router.post(
    "/run",
    response_model=RecordatorioRunResponse,
    status_code=status.HTTP_200_OK,
)
async def run_recordatorios(
    db: DbDep,
    profesional_caller: Annotated[Profesional, Depends(get_profesional_by_api_key)],
    fecha: Annotated[
        date,
        Query(
            description=(
                "Fecha objetivo de los recordatorios (YYYY-MM-DD). "
                "Default: mañana (cubierta por la ventana calculada)."
            )
        ),
    ] = None,
) -> RecordatorioRunResponse:
    """Dispara recordatorios para todos los profesionales activos.

    C-24: el workflow n8n ``flujo-recordatorio.json`` consume este
    endpoint en su cron diario. La ``X-API-Key`` válida autoriza al
    caller; el endpoint itera sobre TODOS los profesionales activos
    (``is_active=True``) — el caller no es el destinatario, es el
    invocador del batch.

    Args:
        fecha: Fecha objetivo (default: ``date.today() + timedelta(days=1)``).
            La ventana calculada cubre los turnos de esa fecha con un
            margen de ±12h.

    Returns:
        ``RecordatorioRunResponse`` con contadores del batch y lista de
        errores recuperables (envíos fallidos, profesionales sin
        ``telegram_bot_token``, etc.).
    """
    if fecha is None:
        fecha = date.today() + timedelta(days=1)

    # El parámetro ``profesional_caller`` solo se usa para que FastAPI
    # valide la auth. El service itera sobre todos los profesionales
    # activos independientemente de quién llamó.
    return await run_recordatorios_para_todos(db, fecha=fecha)
