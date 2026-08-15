import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cancelarTurno, completarTurno, getTurnosHoy } from '../services/turnosHoyService'

export function useTurnosHoy() {
  return useQuery({
    queryKey: ['turnos-hoy'],
    queryFn: getTurnosHoy,
  })
}

function useInvalidateOnSettle() {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: ['turnos-hoy'] })
    queryClient.invalidateQueries({ queryKey: ['metricas'] })
  }
}

export function useCompletarTurno() {
  const invalidate = useInvalidateOnSettle()
  return useMutation({
    mutationFn: completarTurno,
    onSuccess: invalidate,
  })
}

export function useCancelarTurno() {
  const invalidate = useInvalidateOnSettle()
  return useMutation({
    mutationFn: cancelarTurno,
    onSuccess: invalidate,
  })
}
