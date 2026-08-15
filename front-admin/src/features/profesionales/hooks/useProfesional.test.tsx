import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useProfesional } from './useProfesional'
import * as profesionalService from '../services/profesionalService'
import type { ProfesionalAdminResponse } from '../../../shared/types'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useProfesional', () => {
  it('fetches a single profesional by id', async () => {
    const profesional: ProfesionalAdminResponse = {
      id: 9021,
      nombre: 'Dr. Ricardo Mendoza',
      especialidad: 'Odontología general',
      email: 'ricardo@clinica.com',
      is_active: true,
      creado_en: '2026-01-01T00:00:00Z',
    }
    const spy = vi.spyOn(profesionalService, 'getProfesional').mockResolvedValue(profesional)

    const { result } = renderHook(() => useProfesional(9021), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(spy).toHaveBeenCalledWith(9021)
    expect(result.current.data).toEqual(profesional)
  })
})
