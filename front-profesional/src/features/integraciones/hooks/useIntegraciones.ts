import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getIntegraciones, updateIntegraciones } from '../services/integracionesService'

export function useIntegraciones() {
  return useQuery({
    queryKey: ['integraciones'],
    queryFn: getIntegraciones,
  })
}

export function useUpdateIntegraciones() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateIntegraciones,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integraciones'] })
    },
  })
}
