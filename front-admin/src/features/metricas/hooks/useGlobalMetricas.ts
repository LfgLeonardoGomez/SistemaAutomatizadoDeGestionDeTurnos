import { useQuery } from '@tanstack/react-query'
import { getGlobalMetrics } from '../services/metricasService'

export function useGlobalMetricas() {
  return useQuery({
    queryKey: ['metricas-globales'],
    queryFn: getGlobalMetrics,
  })
}
