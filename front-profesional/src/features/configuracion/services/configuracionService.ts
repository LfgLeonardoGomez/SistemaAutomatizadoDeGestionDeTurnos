import { api } from '../../../shared/services/api'
import type { ProfesionalConfig, ProfesionalConfigUpdate } from '../../../shared/types'

export function getConfiguracion() {
  return api.get<ProfesionalConfig>('/profesional/configuracion').then((res) => res.data)
}

export function updateConfiguracion(data: ProfesionalConfigUpdate) {
  return api.put<ProfesionalConfig>('/profesional/configuracion', data).then((res) => res.data)
}
