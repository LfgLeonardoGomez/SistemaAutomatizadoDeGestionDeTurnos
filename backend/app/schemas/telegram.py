from typing import Any

from pydantic import BaseModel


class TelegramUpdate(BaseModel):
    """Minimal wrapper for Telegram Update JSON payload validation."""

    update_id: int
    message: dict[str, Any] | None = None
    callback_query: dict[str, Any] | None = None
