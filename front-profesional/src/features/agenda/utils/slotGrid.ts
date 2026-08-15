function timeToMinutes(time: string): number {
  const [h, m] = time.split(':').map(Number)
  return h * 60 + m
}

function minutesToTime(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

/** Mirrors the backend's app/services/availability_service.py _generate_slots exactly. */
export function generateSlotGrid(horarioInicio: string, horarioFin: string, duracionTurno: number): string[] {
  const inicioMin = timeToMinutes(horarioInicio)
  const finMin = timeToMinutes(horarioFin)
  const slots: string[] = []
  for (let current = inicioMin; current < finMin; current += duracionTurno) {
    slots.push(minutesToTime(current))
  }
  return slots
}
