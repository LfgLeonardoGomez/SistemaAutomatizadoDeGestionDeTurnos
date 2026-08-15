import { useQuery } from '@tanstack/react-query'
import { getMetricas } from '../services/metricasService'

export function useMetricas() {
  return useQuery({
    queryKey: ['metricas'],
    queryFn: getMetricas,
  })
}
