import { api } from '../../../shared/services/api'
import type { ConfirmarTurnoRequest, ReservaTurnoRequest, SlotResponse, Turno } from '../../../shared/types'

export function getDisponibilidad(fecha: string) {
  return api
    .get<SlotResponse[]>('/turnos/disponibles', { params: { fecha } })
    .then((res) => res.data)
}

export function crearReserva(data: ReservaTurnoRequest) {
  return api.post<Turno>('/turnos', data).then((res) => res.data)
}

export function confirmarTurno(turnoId: number, data: ConfirmarTurnoRequest) {
  return api.put<Turno>(`/turnos/${turnoId}/confirmar`, data).then((res) => res.data)
}
