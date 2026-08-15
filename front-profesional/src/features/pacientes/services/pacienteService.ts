import { api } from '../../../shared/services/api'
import type { Paciente, PacienteBusqueda, PacienteConHistorial } from '../../../shared/types'

export async function buscarPorDni(dni: string): Promise<PacienteBusqueda | null> {
  try {
    const { data } = await api.get<PacienteBusqueda>('/pacientes/buscar', { params: { dni } })
    return data
  } catch (error) {
    if (error && typeof error === 'object' && 'response' in error) {
      const status = (error as { response?: { status?: number } }).response?.status
      if (status === 404) return null
    }
    throw error
  }
}

export function listPacientes(params: { limit: number; offset: number }) {
  return api.get<Paciente[]>('/pacientes', { params }).then((res) => res.data)
}

export function getPaciente(id: number) {
  return api.get<PacienteConHistorial>(`/pacientes/${id}`).then((res) => res.data)
}
