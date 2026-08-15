import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useMetricas } from './useMetricas'
import * as metricasService from '../services/metricasService'
import type { Metricas } from '../../../shared/types'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useMetricas', () => {
  it('fetches the metricas using the metricas queryKey', async () => {
    const data: Metricas = { turnos_hoy: 5, tasa_confirmacion_30d: 0.82, tasa_cancelacion_30d: 0.1 }
    vi.spyOn(metricasService, 'getMetricas').mockResolvedValue(data)

    const { result } = renderHook(() => useMetricas(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })
})
