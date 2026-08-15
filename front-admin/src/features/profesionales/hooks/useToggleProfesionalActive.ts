import { useMutation, useQueryClient } from '@tanstack/react-query'
import { activateProfesional, deactivateProfesional } from '../services/profesionalService'

export function useToggleProfesionalActive() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, activate }: { id: number; activate: boolean }) =>
      activate ? activateProfesional(id) : deactivateProfesional(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profesionales'] })
    },
  })
}
