import { api } from '../../../shared/services/api'
import type {
  ProfesionalAdminResponse,
  ProfesionalCreateRequest,
  ProfesionalCreateResponse,
} from '../../../shared/types'

export function listProfesionales(params: { skip: number; limit: number }) {
  return api
    .get<ProfesionalAdminResponse[]>('/admin/profesionales', { params })
    .then((res) => res.data)
}

export function getProfesional(id: number) {
  return api.get<ProfesionalAdminResponse>(`/admin/profesionales/${id}`).then((res) => res.data)
}

export function createProfesional(data: ProfesionalCreateRequest) {
  return api
    .post<ProfesionalCreateResponse>('/admin/profesionales', data)
    .then((res) => res.data)
}

export function activateProfesional(id: number) {
  return api
    .put<ProfesionalAdminResponse>(`/admin/profesionales/${id}/activar`)
    .then((res) => res.data)
}

export function deactivateProfesional(id: number) {
  return api
    .put<ProfesionalAdminResponse>(`/admin/profesionales/${id}/desactivar`)
    .then((res) => res.data)
}
