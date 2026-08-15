import { describe, expect, it, vi } from 'vitest'
import { api } from '../../../shared/services/api'
import { buscarPorDni, getPaciente, listPacientes } from './pacienteService'
import type { Paciente, PacienteBusqueda, PacienteConHistorial } from '../../../shared/types'

describe('pacienteService.buscarPorDni', () => {
  it('calls GET /pacientes/buscar with the dni and returns the paciente', async () => {
    const data: PacienteBusqueda = { id: 5, nombre: 'Juan', apellido: 'Pérez', dni: '12345678', telefono: '555-0001' }
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await buscarPorDni('12345678')

    expect(getSpy).toHaveBeenCalledWith('/pacientes/buscar', { params: { dni: '12345678' } })
    expect(result).toEqual(data)
  })

  it('returns null when the backend responds 404 (paciente not found)', async () => {
    vi.spyOn(api, 'get').mockRejectedValue({ response: { status: 404 } })

    const result = await buscarPorDni('00000000')

    expect(result).toBeNull()
  })
})

describe('pacienteService.listPacientes', () => {
  it('calls GET /pacientes with limit/offset and returns the data', async () => {
    const data: Paciente[] = [
      { id: 5, nombre: 'Juan', apellido: 'Pérez', dni: '12345678', telefono: '555-0001', creado_en: '2026-01-01T00:00:00Z' },
    ]
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await listPacientes({ limit: 100, offset: 0 })

    expect(getSpy).toHaveBeenCalledWith('/pacientes', { params: { limit: 100, offset: 0 } })
    expect(result).toEqual(data)
  })
})

describe('pacienteService.getPaciente', () => {
  it('calls GET /pacientes/{id} and returns the paciente with historial', async () => {
    const data: PacienteConHistorial = {
      id: 5,
      nombre: 'Juan',
      apellido: 'Pérez',
      dni: '12345678',
      telefono: '555-0001',
      creado_en: '2026-01-01T00:00:00Z',
      turnos: [],
    }
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await getPaciente(5)

    expect(getSpy).toHaveBeenCalledWith('/pacientes/5')
    expect(result).toEqual(data)
  })
})
