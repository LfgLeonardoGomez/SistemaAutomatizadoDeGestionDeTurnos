from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from pydantic import ValidationError

from app.config import Settings
from app.schemas.telegram import TelegramUpdate
from app.services.telegram_service import procesar_update_async

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/telegram", status_code=status.HTTP_200_OK, response_model=dict[str, str])
async def recibir_webhook_telegram(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    """Recibe updates de Telegram Bot API.

    Valida el secret token y la estructura del payload.
    Responde 200 inmediatamente y delega el procesamiento a background tasks.
    """
    settings = Settings()
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret token")

    body = await request.json()
    try:
        TelegramUpdate.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed update payload") from exc

    background_tasks.add_task(procesar_update_async, body)
    return {"status": "ok"}
