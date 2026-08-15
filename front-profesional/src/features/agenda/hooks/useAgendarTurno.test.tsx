import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useAgendarTurno } from './useAgendarTurno'
import * as turnoService from '../services/turnoService'
import type { Turno } from '../../../shared/types'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useAgendarTurno', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('creates the reserva and then confirms it with the paciente data', async () => {
    const reservado: Turno = {
      id: 10,
      fecha: '2026-08-19',
      hora_inicio: '09:00',
      hora_fin: '09:30',
      estado: 'RESERVADO_TEMPORAL',
      profesional_id: 1,
      paciente_id: null,
      google_event_id: null,
      creado_en: '2026-08-19T00:00:00Z',
    }
    const confirmado: Turno = { ...reservado, estado: 'CONFIRMADO', paciente_id: 5 }

    const crearSpy = vi.spyOn(turnoService, 'crearReserva').mockResolvedValue(reservado)
    const confirmarSpy = vi.spyOn(turnoService, 'confirmarTurno').mockResolvedValue(confirmado)

    const { result } = renderHook(() => useAgendarTurno(), { wrapper })

    result.current.mutate({
      fecha: '2026-08-19',
      hora_inicio: '09:00',
      paciente: { nombre: 'Juan', apellido: 'Pérez', dni: '12345678', telefono: '555-0001' },
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(crearSpy).toHaveBeenCalledWith({ fecha: '2026-08-19', hora_inicio: '09:00' })
    expect(confirmarSpy).toHaveBeenCalledWith(10, {
      nombre: 'Juan',
      apellido: 'Pérez',
      dni: '12345678',
      telefono: '555-0001',
    })
    expect(result.current.data).toEqual(confirmado)
  })

  it('does not call confirmar if crearReserva fails', async () => {
    vi.spyOn(turnoService, 'crearReserva').mockRejectedValue({ response: { status: 409 } })
    const confirmarSpy = vi.spyOn(turnoService, 'confirmarTurno')

    const { result } = renderHook(() => useAgendarTurno(), { wrapper })
    result.current.mutate({
      fecha: '2026-08-19',
      hora_inicio: '09:00',
      paciente: { nombre: 'Juan', apellido: 'Pérez', dni: '12345678', telefono: '555-0001' },
    })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(confirmarSpy).not.toHaveBeenCalled()
  })
})
