import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useGlobalMetricas } from './useGlobalMetricas'
import * as metricasService from '../services/metricasService'
import type { GlobalMetrics } from '../../../shared/types'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useGlobalMetricas', () => {
  it('fetches the global metrics', async () => {
    const data: GlobalMetrics = {
      total_profesionales: 142,
      profesionales_activos: 128,
      profesionales_inactivos: 14,
      total_turnos: 3482,
      turnos_hoy: 214,
      turnos_confirmados_30d: 2840,
      turnos_cancelados_30d: 642,
      total_pacientes: 8912,
      tasa_confirmacion_30d: 0.815,
      tasa_cancelacion_30d: 0.226,
    }
    vi.spyOn(metricasService, 'getGlobalMetrics').mockResolvedValue(data)

    const { result } = renderHook(() => useGlobalMetricas(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })
})
