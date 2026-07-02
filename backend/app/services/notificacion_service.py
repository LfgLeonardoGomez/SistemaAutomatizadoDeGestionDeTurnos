import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.turno import Turno
from app.models.paciente import Paciente
from app.models.turno_destinatario import TurnoDestinatario
from app.services.telegram_service import enviar_mensaje, format_recordatorio_mensaje, format_recordatorio_keyboard

logger = logging.getLogger(__name__)


async def obtener_turnos_para_recordar(db: AsyncSession, profesional_id: int, horas_antes: int) -> list[Turno]:
    """Query turnos CONFIRMADO sin recordatorio dentro de la ventana de horas.

    Filtra por estado, recordatorio_enviado y rango de fecha/hora.
    Usa SELECT FOR UPDATE para prevenir race conditions.
    """
    ahora = datetime.now()
    limite = ahora + timedelta(hours=horas_antes)

    stmt = (
        select(Turno)
        .join(Paciente)
        .where(
            Turno.estado == "CONFIRMADO",
            Turno.recordatorio_enviado == False,
            Turno.fecha <= limite.date(),
            Turno.profesional_id == profesional_id,
        )
        .with_for_update()
    )
    result = await db.execute(stmt)
    turnos = result.scalars().all()

    candidatos: list[Turno] = []
    for turno in turnos:
        dt = datetime.combine(turno.fecha, turno.hora_inicio)
        if ahora <= dt <= limite:
            candidatos.append(turno)

    return candidatos


async def enviar_recordatorio_telegram(turno: Turno, bot_token: str) -> bool:
    """Envía un recordatorio por Telegram al destinatario del turno (C-23).

    Cambio de comportamiento (C-23): el destinatario se lee del turno
    (``turno.destinatarios`` filtrado por canal='TELEGRAM'), no de
    ``paciente.telegram_chat_id`` (columna eliminada por ser código muerto:
    nunca se escribía, por lo que el job anterior siempre leía ``None`` y
    marcaba ``recordatorio_enviado=True`` sin enviar nada).

    Retorna True si el envío fue exitoso o si no hay destinatario TELEGRAM
    configurado (caso esperado: turno legacy o turno administrativo — se
    marca como enviado y se loguea warning, sin reintento).
    Retorna False si el envío falló (permite reintento).
    """
    # C-23: destinatario por turno, no por paciente. Esto cubre el caso
    # multi-chat (un DNI con varios chats) y arregla el bug del recordatorio
    # silenciosamente roto.
    chat_id: str | None = None
    for dest in turno.destinatarios:
        if dest.canal == "TELEGRAM":
            chat_id = dest.destinatario
            break

    if chat_id is None:
        paciente_id = turno.paciente_id if turno.paciente_id is not None else "?"
        logger.warning(
            f"Turno {turno.id} (paciente={paciente_id}) no tiene destinatario "
            f"TELEGRAM configurado; marcando recordatorio_enviado=True sin enviar."
        )
        return True

    paciente = turno.paciente
    paciente_nombre = paciente.nombre if paciente is not None else ""
    paciente_apellido = paciente.apellido if paciente is not None else ""

    mensaje = format_recordatorio_mensaje(
        turno={
            "fecha": turno.fecha,
            "hora_inicio": turno.hora_inicio,
        },
        paciente={
            "nombre": paciente_nombre,
            "apellido": paciente_apellido,
        },
    )
    keyboard = format_recordatorio_keyboard(turno.id)
    ok = await enviar_mensaje(int(chat_id), mensaje, bot_token, keyboard)
    if not ok:
        logger.error(f"Error enviando recordatorio Telegram para turno {turno.id}")
    return ok


async def marcar_recordatorio_enviado(db: AsyncSession, turno_id: int, profesional_id: int) -> None:
    """Marca el turno como recordatorio_enviado = True. Patrón A: no commitea."""
    result = await db.execute(
        select(Turno).where(Turno.id == turno_id, Turno.profesional_id == profesional_id)
    )
    turno = result.scalar_one_or_none()
    if turno is not None:
        turno.recordatorio_enviado = True
        # Patrón A: el caller (scheduler) hace commit.
        logger.info(f"Turno {turno_id} marcado como recordatorio_enviado=True")
    else:
        logger.warning(f"No se encontró turno {turno_id} para marcar recordatorio_enviado")
