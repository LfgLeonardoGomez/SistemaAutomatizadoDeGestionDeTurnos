import { api } from '../../../shared/services/api'
import type { Metricas } from '../../../shared/types'

export function getMetricas() {
  return api.get<Metricas>('/profesional/metricas').then((res) => res.data)
}
