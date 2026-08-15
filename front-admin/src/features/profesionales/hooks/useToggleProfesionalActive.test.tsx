import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useToggleProfesionalActive } from './useToggleProfesionalActive'
import * as profesionalService from '../services/profesionalService'
import type { ProfesionalAdminResponse } from '../../../shared/types'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return (
    <QueryClientProvider client={queryClient}>
      <CaptureQueryClient client={queryClient}>{children}</CaptureQueryClient>
    </QueryClientProvider>
  )
}

let capturedQueryClient: QueryClient

function CaptureQueryClient({ client, children }: { client: QueryClient; children: ReactNode }) {
  capturedQueryClient = client
  return <>{children}</>
}

const profesional: ProfesionalAdminResponse = {
  id: 9021,
  nombre: 'Dr. Ricardo Mendoza',
  especialidad: 'Odontología general',
  email: 'ricardo@clinica.com',
  is_active: true,
  creado_en: '2026-01-01T00:00:00Z',
}

describe('useToggleProfesionalActive', () => {
  it('calls activateProfesional when activate is true and invalidates the profesionales query', async () => {
    const spy = vi.spyOn(profesionalService, 'activateProfesional').mockResolvedValue({
      ...profesional,
      is_active: true,
    })
    const { result } = renderHook(() => useToggleProfesionalActive(), { wrapper })
    const invalidateSpy = vi.spyOn(capturedQueryClient, 'invalidateQueries')

    result.current.mutate({ id: 9021, activate: true })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(spy).toHaveBeenCalledWith(9021)
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['profesionales'] })
  })

  it('calls deactivateProfesional when activate is false', async () => {
    const spy = vi.spyOn(profesionalService, 'deactivateProfesional').mockResolvedValue({
      ...profesional,
      is_active: false,
    })
    const { result } = renderHook(() => useToggleProfesionalActive(), { wrapper })

    result.current.mutate({ id: 9021, activate: false })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(spy).toHaveBeenCalledWith(9021)
  })
})
