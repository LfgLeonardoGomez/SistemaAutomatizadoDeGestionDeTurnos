import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useDisponibilidad } from './useDisponibilidad'
import * as turnoService from '../services/turnoService'
import * as configuracionService from '../../configuracion/services/configuracionService'
import type { ProfesionalConfig, SlotResponse } from '../../../shared/types'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const config: ProfesionalConfig = {
  horario_inicio: '09:00',
  horario_fin: '11:00',
  dias_atencion: ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'],
  duracion_turno: 30,
  especialidad: 'Odontología general',
}

describe('useDisponibilidad', () => {
  it('marks grid slots not present in the disponibles response as ocupado', async () => {
    vi.spyOn(configuracionService, 'getConfiguracion').mockResolvedValue(config)
    const disponibles: SlotResponse[] = [
      { hora_inicio: '09:00', hora_fin: '09:30', disponible: true },
      { hora_inicio: '10:30', hora_fin: '11:00', disponible: true },
    ]
    vi.spyOn(turnoService, 'getDisponibilidad').mockResolvedValue(disponibles)

    const { result } = renderHook(() => useDisponibilidad('2026-08-19'), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.slots).toEqual([
      { hora_inicio: '09:00', hora_fin: '09:30', disponible: true },
      { hora_inicio: '09:30', hora_fin: '10:00', disponible: false },
      { hora_inicio: '10:00', hora_fin: '10:30', disponible: false },
      { hora_inicio: '10:30', hora_fin: '11:00', disponible: true },
    ])
  })

  it('reports counts of available and occupied slots', async () => {
    vi.spyOn(configuracionService, 'getConfiguracion').mockResolvedValue(config)
    vi.spyOn(turnoService, 'getDisponibilidad').mockResolvedValue([
      { hora_inicio: '09:00', hora_fin: '09:30', disponible: true },
    ])

    const { result } = renderHook(() => useDisponibilidad('2026-08-19'), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.disponiblesCount).toBe(1)
    expect(result.current.ocupadosCount).toBe(3)
  })
})
