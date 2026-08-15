import { describe, expect, it, vi } from 'vitest'
import { api } from '../../../shared/services/api'
import { cancelarTurno, completarTurno, getTurnosHoy } from './turnosHoyService'
import type { TurnoConPaciente } from '../../../shared/types'

describe('turnosHoyService.getTurnosHoy', () => {
  it('calls GET /profesional/turnos-hoy and returns the data', async () => {
    const data: TurnoConPaciente[] = [
      {
        id: 1,
        fecha: '2026-08-15',
        hora_inicio: '09:00',
        hora_fin: '09:30',
        estado: 'CONFIRMADO',
        profesional_id: 1,
        paciente_id: 5,
        paciente: { id: 5, nombre: 'Juan', apellido: 'Pérez', dni: '12345678', telefono: '555-0001' },
      },
    ]
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await getTurnosHoy()

    expect(getSpy).toHaveBeenCalledWith('/profesional/turnos-hoy')
    expect(result).toEqual(data)
  })
})

describe('turnosHoyService.completarTurno / cancelarTurno', () => {
  it('calls PUT /turnos/{id}/completar', async () => {
    const putSpy = vi.spyOn(api, 'put').mockResolvedValue({ data: {} })
    await completarTurno(1)
    expect(putSpy).toHaveBeenCalledWith('/turnos/1/completar')
  })

  it('calls PUT /turnos/{id}/cancelar', async () => {
    const putSpy = vi.spyOn(api, 'put').mockResolvedValue({ data: {} })
    await cancelarTurno(1)
    expect(putSpy).toHaveBeenCalledWith('/turnos/1/cancelar')
  })
})
