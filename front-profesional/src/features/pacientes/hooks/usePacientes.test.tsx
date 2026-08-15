import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { usePacientes } from './usePacientes'
import * as pacienteService from '../services/pacienteService'
import type { Paciente } from '../../../shared/types'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('usePacientes', () => {
  it('fetches the pacientes list with limit=100, offset=0 by default', async () => {
    const data: Paciente[] = [
      { id: 5, nombre: 'Juan', apellido: 'Pérez', dni: '12345678', telefono: '555-0001', creado_en: '2026-01-01T00:00:00Z' },
    ]
    const spy = vi.spyOn(pacienteService, 'listPacientes').mockResolvedValue(data)

    const { result } = renderHook(() => usePacientes(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(spy).toHaveBeenCalledWith({ limit: 100, offset: 0 })
    expect(result.current.data).toEqual(data)
  })
})
