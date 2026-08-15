import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useConfiguracion, useUpdateConfiguracion } from './useConfiguracion'
import * as configuracionService from '../services/configuracionService'
import type { ProfesionalConfig } from '../../../shared/types'

const config: ProfesionalConfig = {
  horario_inicio: '09:00',
  horario_fin: '17:00',
  dias_atencion: ['Lunes', 'Martes'],
  duracion_turno: 30,
  especialidad: 'Odontología general',
}

describe('useConfiguracion', () => {
  it('fetches the configuracion', async () => {
    vi.spyOn(configuracionService, 'getConfiguracion').mockResolvedValue(config)
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { result } = renderHook(() => useConfiguracion(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(config)
  })
})

describe('useUpdateConfiguracion', () => {
  it('calls updateConfiguracion and invalidates the configuracion query', async () => {
    const updated = { ...config, duracion_turno: 45 }
    vi.spyOn(configuracionService, 'updateConfiguracion').mockResolvedValue(updated)

    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const { result } = renderHook(() => useUpdateConfiguracion(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    })

    result.current.mutate({ duracion_turno: 45 })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['profesional-configuracion'] })
  })
})
