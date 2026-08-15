import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getConfiguracion, updateConfiguracion } from '../services/configuracionService'

export function useConfiguracion() {
  return useQuery({
    queryKey: ['profesional-configuracion'],
    queryFn: getConfiguracion,
  })
}

export function useUpdateConfiguracion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateConfiguracion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profesional-configuracion'] })
    },
  })
}
