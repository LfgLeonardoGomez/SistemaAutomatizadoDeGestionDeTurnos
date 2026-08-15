import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DashboardPage from './DashboardPage'
import * as turnosHoyService from '../services/turnosHoyService'
import type { Turno, TurnoConPaciente } from '../../../shared/types'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>,
  )
}

function buildTurno(overrides: Partial<TurnoConPaciente> = {}): TurnoConPaciente {
  return {
    id: 1,
    fecha: '2026-08-15',
    hora_inicio: '09:00',
    hora_fin: '09:30',
    estado: 'CONFIRMADO',
    profesional_id: 1,
    paciente_id: 5,
    paciente: { id: 5, nombre: 'Juan', apellido: 'Pérez', dni: '12345678', telefono: '555-0001' },
    ...overrides,
  }
}

function buildTurnoResponse(overrides: Partial<Turno> = {}): Turno {
  return {
    id: 1,
    fecha: '2026-08-15',
    hora_inicio: '09:00',
    hora_fin: '09:30',
    estado: 'COMPLETADO',
    profesional_id: 1,
    paciente_id: 5,
    google_event_id: null,
    creado_en: '2026-08-01T00:00:00Z',
    ...overrides,
  }
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a loading skeleton while fetching', () => {
    vi.spyOn(turnosHoyService, 'getTurnosHoy').mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByRole('status', { name: /cargando/i })).toBeInTheDocument()
  })

  it('shows an empty state when there are no turnos today', async () => {
    vi.spyOn(turnosHoyService, 'getTurnosHoy').mockResolvedValue([])
    renderPage()
    expect(await screen.findByText(/no tenés turnos programados para hoy/i)).toBeInTheDocument()
  })

  it('renders the turno count and the list once loaded', async () => {
    vi.spyOn(turnosHoyService, 'getTurnosHoy').mockResolvedValue([
      buildTurno(),
      buildTurno({
        id: 2,
        paciente: { id: 6, nombre: 'Lucía', apellido: 'Ferreyra', dni: '87654321', telefono: '555-0002' },
      }),
    ])
    renderPage()
    expect(await screen.findByText('Juan Pérez')).toBeInTheDocument()
    expect(screen.getByText('Lucía Ferreyra')).toBeInTheDocument()
    expect(screen.getByText(/2 turnos/i)).toBeInTheDocument()
  })

  it('completes a turno directly without confirmation', async () => {
    vi.spyOn(turnosHoyService, 'getTurnosHoy').mockResolvedValue([buildTurno()])
    const completarSpy = vi.spyOn(turnosHoyService, 'completarTurno').mockResolvedValue(buildTurnoResponse())
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Juan Pérez')
    await user.click(screen.getByRole('button', { name: /completar/i }))

    expect(completarSpy).toHaveBeenCalledWith(1, expect.anything())
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('asks for confirmation before cancelling a turno', async () => {
    vi.spyOn(turnosHoyService, 'getTurnosHoy').mockResolvedValue([buildTurno()])
    const cancelarSpy = vi.spyOn(turnosHoyService, 'cancelarTurno').mockResolvedValue(buildTurnoResponse())
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Juan Pérez')
    await user.click(screen.getByRole('button', { name: /^cancelar$/i }))

    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText(/¿estás seguro/i)).toBeInTheDocument()
    expect(cancelarSpy).not.toHaveBeenCalled()

    await user.click(within(dialog).getByRole('button', { name: /^cancelar turno$/i }))
    expect(cancelarSpy).toHaveBeenCalledWith(1, expect.anything())
  })
})
