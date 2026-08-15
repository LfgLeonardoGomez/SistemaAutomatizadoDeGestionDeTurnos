import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useIntegraciones, useUpdateIntegraciones } from './useIntegraciones'
import * as integracionesService from '../services/integracionesService'
import type { Integraciones } from '../../../shared/types'

const integraciones: Integraciones = { has_telegram: false, has_google: false, google_calendar_id: 'primary' }

describe('useIntegraciones', () => {
  it('fetches the integraciones', async () => {
    vi.spyOn(integracionesService, 'getIntegraciones').mockResolvedValue(integraciones)
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { result } = renderHook(() => useIntegraciones(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(integraciones)
  })
})

describe('useUpdateIntegraciones', () => {
  it('calls updateIntegraciones and invalidates the integraciones query', async () => {
    vi.spyOn(integracionesService, 'updateIntegraciones').mockResolvedValue({
      ...integraciones,
      has_telegram: true,
    })

    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const { result } = renderHook(() => useUpdateIntegraciones(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    })

    result.current.mutate({ telegram_bot_token: 'abc123' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['integraciones'] })
  })
})
