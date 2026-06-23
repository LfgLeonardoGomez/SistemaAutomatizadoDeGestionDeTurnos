from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError

from app.dependencies import get_profesional_by_telegram_secret_token
from app.models.profesional import Profesional
from app.schemas.telegram import TelegramUpdate
from app.services.telegram_service import procesar_update_async

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/telegram", status_code=status.HTTP_200_OK, response_model=dict[str, str])
async def recibir_webhook_telegram(
    request: Request,
    background_tasks: BackgroundTasks,
    profesional: Annotated[Profesional, Depends(get_profesional_by_telegram_secret_token)],
) -> dict[str, str]:
    """Recibe updates de Telegram Bot API.

    Valida el secret token y la estructura del payload.
    Responde 200 inmediatamente y delega el procesamiento a background tasks.
    """
    body = await request.json()
    try:
        TelegramUpdate.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed update payload") from exc

    background_tasks.add_task(procesar_update_async, body, profesional_id=profesional.id)
    return {"status": "ok"}
