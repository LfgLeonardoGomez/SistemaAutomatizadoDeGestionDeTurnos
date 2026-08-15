import { useMutation, useQueryClient } from '@tanstack/react-query'
import { confirmarTurno, crearReserva } from '../services/turnoService'
import type { ConfirmarTurnoRequest } from '../../../shared/types'

interface AgendarTurnoInput {
  fecha: string
  hora_inicio: string
  paciente: ConfirmarTurnoRequest
}

export function useAgendarTurno() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ fecha, hora_inicio, paciente }: AgendarTurnoInput) => {
      const reservado = await crearReserva({ fecha, hora_inicio })
      return confirmarTurno(reservado.id, paciente)
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['disponibilidad', variables.fecha] })
      queryClient.invalidateQueries({ queryKey: ['turnos-hoy'] })
      queryClient.invalidateQueries({ queryKey: ['metricas'] })
    },
  })
}
