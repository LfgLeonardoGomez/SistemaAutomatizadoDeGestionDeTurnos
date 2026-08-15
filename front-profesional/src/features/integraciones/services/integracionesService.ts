import { api } from '../../../shared/services/api'
import type { Integraciones, IntegracionesUpdate } from '../../../shared/types'

export function getIntegraciones() {
  return api.get<Integraciones>('/profesional/integraciones').then((res) => res.data)
}

export function updateIntegraciones(data: IntegracionesUpdate) {
  return api.put<Integraciones>('/profesional/integraciones', data).then((res) => res.data)
}
