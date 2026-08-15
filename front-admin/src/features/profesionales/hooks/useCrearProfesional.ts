import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createProfesional } from '../services/profesionalService'

export function useCrearProfesional() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createProfesional,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profesionales'] })
    },
  })
}
