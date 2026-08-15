import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useProfesionales } from './useProfesionales'
import * as profesionalService from '../services/profesionalService'
import type { ProfesionalAdminResponse } from '../../../shared/types'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useProfesionales', () => {
  it('fetches the profesionales list with skip=0, limit=100 by default', async () => {
    const data: ProfesionalAdminResponse[] = [
      {
        id: 1,
        nombre: 'Dr. Ricardo Mendoza',
        especialidad: 'Odontología general',
        email: 'ricardo@clinica.com',
        is_active: true,
        creado_en: '2026-01-01T00:00:00Z',
      },
    ]
    const spy = vi.spyOn(profesionalService, 'listProfesionales').mockResolvedValue(data)

    const { result } = renderHook(() => useProfesionales(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(spy).toHaveBeenCalledWith({ skip: 0, limit: 100 })
    expect(result.current.data).toEqual(data)
  })
})
