import { describe, expect, it, vi } from 'vitest'
import { api } from '../../../shared/services/api'
import { confirmarTurno, crearReserva, getDisponibilidad } from './turnoService'
import type { SlotResponse, Turno } from '../../../shared/types'

describe('turnoService.getDisponibilidad', () => {
  it('calls GET /turnos/disponibles with the fecha and returns the data', async () => {
    const data: SlotResponse[] = [{ hora_inicio: '09:00', hora_fin: '09:30', disponible: true }]
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await getDisponibilidad('2026-08-15')

    expect(getSpy).toHaveBeenCalledWith('/turnos/disponibles', { params: { fecha: '2026-08-15' } })
    expect(result).toEqual(data)
  })
})

describe('turnoService.crearReserva', () => {
  it('calls POST /turnos with fecha, hora_inicio and returns the created turno', async () => {
    const turno: Turno = {
      id: 10,
      fecha: '2026-08-15',
      hora_inicio: '09:00',
      hora_fin: '09:30',
      estado: 'RESERVADO_TEMPORAL',
      profesional_id: 1,
      paciente_id: null,
      google_event_id: null,
      creado_en: '2026-08-15T00:00:00Z',
    }
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: turno })

    const result = await crearReserva({ fecha: '2026-08-15', hora_inicio: '09:00' })

    expect(postSpy).toHaveBeenCalledWith('/turnos', { fecha: '2026-08-15', hora_inicio: '09:00' })
    expect(result).toEqual(turno)
  })
})

describe('turnoService.confirmarTurno', () => {
  it('calls PUT /turnos/{id}/confirmar with paciente data and returns the confirmed turno', async () => {
    const turno: Turno = {
      id: 10,
      fecha: '2026-08-15',
      hora_inicio: '09:00',
      hora_fin: '09:30',
      estado: 'CONFIRMADO',
      profesional_id: 1,
      paciente_id: 5,
      google_event_id: null,
      creado_en: '2026-08-15T00:00:00Z',
    }
    const putSpy = vi.spyOn(api, 'put').mockResolvedValue({ data: turno })

    const payload = { nombre: 'Juan', apellido: 'Pérez', dni: '12345678', telefono: '555-0001' }
    const result = await confirmarTurno(10, payload)

    expect(putSpy).toHaveBeenCalledWith('/turnos/10/confirmar', payload)
    expect(result).toEqual(turno)
  })
})
