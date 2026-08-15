import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useCancelarTurno, useCompletarTurno, useTurnosHoy } from './useTurnosHoy'
import * as turnosHoyService from '../services/turnosHoyService'
import type { Turno, TurnoConPaciente } from '../../../shared/types'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useTurnosHoy', () => {
  it('fetches the turnos del día', async () => {
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
    vi.spyOn(turnosHoyService, 'getTurnosHoy').mockResolvedValue(data)

    const { result } = renderHook(() => useTurnosHoy(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })
})

describe('useCompletarTurno', () => {
  it('calls completarTurno and invalidates turnos-hoy and metricas', async () => {
    const turno: Turno = {
      id: 1,
      fecha: '2026-08-15',
      hora_inicio: '09:00',
      hora_fin: '09:30',
      estado: 'COMPLETADO',
      profesional_id: 1,
      paciente_id: 5,
      google_event_id: null,
      creado_en: '2026-08-01T00:00:00Z',
    }
    vi.spyOn(turnosHoyService, 'completarTurno').mockResolvedValue(turno)

    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const { result } = renderHook(() => useCompletarTurno(), {
      wrapper: ({ children }) => <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>,
    })

    result.current.mutate(1)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['turnos-hoy'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['metricas'] })
  })
})

describe('useCancelarTurno', () => {
  it('calls cancelarTurno and invalidates turnos-hoy and metricas', async () => {
    const turno: Turno = {
      id: 1,
      fecha: '2026-08-15',
      hora_inicio: '09:00',
      hora_fin: '09:30',
      estado: 'CANCELADO',
      profesional_id: 1,
      paciente_id: 5,
      google_event_id: null,
      creado_en: '2026-08-01T00:00:00Z',
    }
    vi.spyOn(turnosHoyService, 'cancelarTurno').mockResolvedValue(turno)

    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const { result } = renderHook(() => useCancelarTurno(), {
      wrapper: ({ children }) => <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>,
    })

    result.current.mutate(1)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['turnos-hoy'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['metricas'] })
  })
})
