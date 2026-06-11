from datetime import date, time
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profesional import Profesional
from app.models.turno import Turno

DIAS_SEMANA = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


def _time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _minutes_to_str(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _generate_slots(horario_inicio: str, horario_fin: str, duracion: int) -> List[str]:
    inicio_min = _time_to_minutes(time.fromisoformat(horario_inicio))
    fin_min = _time_to_minutes(time.fromisoformat(horario_fin))
    slots = []
    current = inicio_min
    while current < fin_min:
        slots.append(_minutes_to_str(current))
        current += duracion
    return slots


async def calcular_disponibilidad(
    db: AsyncSession,
    fecha: date,
    profesional_id: int = 1,
) -> List[str]:
    """Calcula los horarios de inicio disponibles para una fecha dada."""
    result = await db.execute(
        select(Profesional).where(Profesional.id == profesional_id)
    )
    profesional = result.scalar_one_or_none()
    if not profesional:
        return []

    dia_nombre = DIAS_SEMANA.get(fecha.weekday())
    if dia_nombre not in profesional.dias_atencion:
        return []

    slots = _generate_slots(
        profesional.horario_inicio,
        profesional.horario_fin,
        profesional.duracion_turno,
    )

    result = await db.execute(
        select(Turno).where(
            Turno.fecha == fecha,
            Turno.estado.in_(["CONFIRMADO", "RESERVADO_TEMPORAL"]),
            Turno.profesional_id == profesional_id,
        )
    )
    turnos = result.scalars().all()

    disponibles = []
    for slot_str in slots:
        slot_start_min = _time_to_minutes(time.fromisoformat(slot_str))
        slot_end_min = slot_start_min + profesional.duracion_turno

        ocupado = False
        for turno in turnos:
            turno_start_min = _time_to_minutes(turno.hora_inicio)
            turno_end_min = _time_to_minutes(turno.hora_fin)
            if slot_start_min < turno_end_min and slot_end_min > turno_start_min:
                ocupado = True
                break
        if not ocupado:
            disponibles.append(slot_str)

    return disponibles
