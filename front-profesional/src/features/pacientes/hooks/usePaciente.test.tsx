import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { usePaciente } from './usePaciente'
import * as pacienteService from '../services/pacienteService'
import type { PacienteConHistorial } from '../../../shared/types'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('usePaciente', () => {
  it('fetches a single paciente by id', async () => {
    const data: PacienteConHistorial = {
      id: 5,
      nombre: 'Juan',
      apellido: 'Pérez',
      dni: '12345678',
      telefono: '555-0001',
      creado_en: '2026-01-01T00:00:00Z',
      turnos: [],
    }
    const spy = vi.spyOn(pacienteService, 'getPaciente').mockResolvedValue(data)

    const { result } = renderHook(() => usePaciente(5), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(spy).toHaveBeenCalledWith(5)
    expect(result.current.data).toEqual(data)
  })
})
