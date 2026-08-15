import { api } from '../../../shared/services/api'
import type { GlobalMetrics } from '../../../shared/types'

export function getGlobalMetrics() {
  return api.get<GlobalMetrics>('/admin/metricas').then((res) => res.data)
}
