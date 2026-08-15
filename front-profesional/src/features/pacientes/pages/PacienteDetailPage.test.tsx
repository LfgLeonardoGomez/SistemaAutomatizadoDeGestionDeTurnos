import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import PacienteDetailPage from './PacienteDetailPage'
import * as pacienteService from '../services/pacienteService'
import type { PacienteConHistorial } from '../../../shared/types'

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/pacientes/:id" element={<PacienteDetailPage />} />
          <Route path="/pacientes" element={<div>Listado de pacientes</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('PacienteDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a loading skeleton while fetching', () => {
    vi.spyOn(pacienteService, 'getPaciente').mockReturnValue(new Promise(() => {}))
    renderAt('/pacientes/5')
    expect(screen.getByRole('status', { name: /cargando/i })).toBeInTheDocument()
  })

  it('renders the paciente data and historial on success', async () => {
    const paciente: PacienteConHistorial = {
      id: 5,
      nombre: 'Juan',
      apellido: 'Pérez',
      dni: '12345678',
      telefono: '555-0001',
      creado_en: '2026-01-01T00:00:00Z',
      turnos: [
        {
          id: 1,
          fecha: '2026-08-10',
          hora_inicio: '09:00',
          hora_fin: '09:30',
          estado: 'COMPLETADO',
          profesional_id: 1,
          paciente_id: 5,
          google_event_id: null,
          creado_en: '2026-08-01T00:00:00Z',
        },
      ],
    }
    vi.spyOn(pacienteService, 'getPaciente').mockResolvedValue(paciente)
    renderAt('/pacientes/5')

    expect(await screen.findByText('Juan Pérez')).toBeInTheDocument()
    expect(screen.getByText('12345678')).toBeInTheDocument()
    expect(screen.getByText('10/08/2026')).toBeInTheDocument()
  })

  it('calls getPaciente with the id from the route params', async () => {
    const spy = vi.spyOn(pacienteService, 'getPaciente').mockResolvedValue({
      id: 5,
      nombre: 'Juan',
      apellido: 'Pérez',
      dni: '12345678',
      telefono: '555-0001',
      creado_en: '2026-01-01T00:00:00Z',
      turnos: [],
    })
    renderAt('/pacientes/5')
    await screen.findByText('Juan Pérez')
    expect(spy).toHaveBeenCalledWith(5)
  })

  it('shows a not-found message and a link back to the list on 404', async () => {
    vi.spyOn(pacienteService, 'getPaciente').mockRejectedValue({ response: { status: 404 } })
    renderAt('/pacientes/9999')

    expect(await screen.findByText(/paciente no encontrado/i)).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /volver al listado/i })
    expect(link).toHaveAttribute('href', '/pacientes')
  })
})
