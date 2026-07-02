"""Schemas Pydantic del módulo de recordatorios (C-24).

Cubre el contrato de respuesta de ``POST /api/v1/recordatorios/run``:
``RecordatorioRunResponse`` agrega un ``RecordatorioError`` por cada fallo
recuperable (envío a Telegram falló, profesional sin ``telegram_bot_token``,
etc.) sin abortar el batch completo.
"""
from datetime import date

from pydantic import BaseModel


class RecordatorioError(BaseModel):
    """Detalle de un fallo no-fatal durante el run de recordatorios.

    Attributes:
        profesional_id: ID del profesional al que pertenece el turno (o al
            que se intentó enviar sin éxito).
        turno_id: ID del turno cuyo envío falló. ``None`` cuando el error
            es a nivel profesional (p.ej. sin ``telegram_bot_token``
            configurado) y no hay un turno específico asociado.
        mensaje: Descripción legible para ops del fallo.
    """

    profesional_id: int
    turno_id: int | None
    mensaje: str


class RecordatorioRunResponse(BaseModel):
    """Respuesta agregada de ``POST /api/v1/recordatorios/run`` (C-24).

    Itera por todos los profesionales activos y devuelve contadores del
    batch. Un profesional con fallos no aborta el batch — los errores se
    devuelven en ``errores`` para diagnóstico de ops.

    Attributes:
        fecha: Fecha objetivo del run (la ventana de recordatorios cubre
            los turnos cuya ``fecha`` cae en torno a este día).
        total_candidatos: Turnos CONFIRMADOS sin recordatorio previo que
            cayeron dentro de la ventana calculada para ``fecha``.
        total_enviados: Turnos cuyo envío fue exitoso (o que no tenían
            destinatario TELEGRAM — se marcan como enviados sin enviar).
        total_fallidos: Turnos cuyo envío falló; reintentables en el
            próximo run.
        errores: Lista de errores recuperables, agregados para ops.
    """

    fecha: date
    total_candidatos: int
    total_enviados: int
    total_fallidos: int
    errores: list[RecordatorioError]
