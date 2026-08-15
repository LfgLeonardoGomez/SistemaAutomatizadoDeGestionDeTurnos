import { api } from '../../../shared/services/api'
import type { Turno, TurnoConPaciente } from '../../../shared/types'

export function getTurnosHoy() {
  return api.get<TurnoConPaciente[]>('/profesional/turnos-hoy').then((res) => res.data)
}

export function completarTurno(turnoId: number) {
  return api.put<Turno>(`/turnos/${turnoId}/completar`).then((res) => res.data)
}

export function cancelarTurno(turnoId: number) {
  return api.put<Turno>(`/turnos/${turnoId}/cancelar`).then((res) => res.data)
}
