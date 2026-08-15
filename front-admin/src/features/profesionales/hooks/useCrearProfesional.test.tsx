import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useCrearProfesional } from './useCrearProfesional'
import * as profesionalService from '../services/profesionalService'
import type { ProfesionalCreateResponse } from '../../../shared/types'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useCrearProfesional', () => {
  it('creates a profesional and returns the response with generated credentials', async () => {
    const response: ProfesionalCreateResponse = {
      id: 5,
      nombre: 'Dr. Alejandro Méndez',
      email: 'alejandro@clinica.com',
      especialidad: 'Ortodoncia',
      is_active: true,
      duracion_turno: 30,
      horario_inicio: '09:00',
      horario_fin: '18:00',
      dias_atencion: ['lunes'],
      api_key: 'pk_live_abc123',
      telegram_secret_token: 'tg_secret_xyz',
    }
    vi.spyOn(profesionalService, 'createProfesional').mockResolvedValue(response)

    const { result } = renderHook(() => useCrearProfesional(), { wrapper })
    result.current.mutate({
      nombre: 'Dr. Alejandro Méndez',
      email: 'alejandro@clinica.com',
      especialidad: 'Ortodoncia',
      password: 'password123',
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(response)
  })
})
