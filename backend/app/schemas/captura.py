from typing import Any, Optional

from pydantic import BaseModel, Field


class CapturaPendienteResponse(BaseModel):
    """State of the Telegram data-capture conversation for one booking.

    ``paso`` is derived from ``datos`` on every read (see
    ``captura_service.derivar_paso``) — it is not a stored column, so it can
    never contradict the captured data.
    """

    turno_id: int
    paso: str
    datos: dict[str, Any]


class ActualizarCapturaRequest(BaseModel):
    """One answer (or several) to merge into the capture.

    Merged, not replaced: each Telegram message carries a single answer and
    must not wipe the ones captured before it.
    """

    datos: dict[str, Any] = Field(default_factory=dict)
