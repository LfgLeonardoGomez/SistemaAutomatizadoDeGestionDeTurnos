import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.turno import Turno
from app.models.paciente import Paciente
from app.services.telegram_service import enviar_mensaje, format_recordatorio_mensaje, format_recordatorio_keyboard

logger = logging.getLogger(__name__)


async def obtener_turnos_para_recordar(db: AsyncSession, horas_antes: int) -> list[Turno]:
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


async def enviar_recordatorio_telegram(turno: Turno) -> bool:
    """Envía un recordatorio por Telegram al paciente del turno.

    Retorna True si el envío fue exitoso o si no hay chat_id (para marcar flag).
    Retorna False si el envío falló (permitir reintento).
    """
    paciente = turno.paciente
    if paciente is None:
        logger.warning(f"Turno {turno.id} no tiene paciente asociado")
        return True

    chat_id = paciente.telegram_chat_id
    if chat_id is None:
        logger.warning(
            f"Paciente {paciente.id} no tiene chat_id de Telegram; "
            f"marcando recordatorio_enviado=True para turno {turno.id}"
        )
        return True

    try:
        mensaje = format_recordatorio_mensaje(
            turno={
                "fecha": turno.fecha,
                "hora_inicio": turno.hora_inicio,
            },
            paciente={
                "nombre": paciente.nombre,
                "apellido": paciente.apellido,
            },
        )
        keyboard = format_recordatorio_keyboard(turno.id)
        await enviar_mensaje(int(chat_id), mensaje, keyboard)
        return True
    except Exception as exc:
        logger.error(f"Error enviando recordatorio Telegram para turno {turno.id}: {exc}")
        return False


async def marcar_recordatorio_enviado(db: AsyncSession, turno_id: int) -> None:
    """Marca el turno como recordatorio_enviado = True."""
    result = await db.execute(select(Turno).where(Turno.id == turno_id))
    turno = result.scalar_one_or_none()
    if turno is not None:
        turno.recordatorio_enviado = True
        await db.commit()
        logger.info(f"Turno {turno_id} marcado como recordatorio_enviado=True")
    else:
        logger.warning(f"No se encontró turno {turno_id} para marcar recordatorio_enviado")
