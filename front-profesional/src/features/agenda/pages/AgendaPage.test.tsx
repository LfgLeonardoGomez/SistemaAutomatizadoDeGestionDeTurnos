import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AgendaPage from './AgendaPage'
import * as turnoService from '../services/turnoService'
import * as configuracionService from '../../configuracion/services/configuracionService'
import type { ProfesionalConfig, SlotResponse, Turno } from '../../../shared/types'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <AgendaPage />
    </QueryClientProvider>,
  )
}

const config: ProfesionalConfig = {
  horario_inicio: '09:00',
  horario_fin: '10:00',
  dias_atencion: ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'],
  duracion_turno: 30,
  especialidad: 'Odontología general',
}

describe('AgendaPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows the slot summary and slots for the selected date', async () => {
    vi.spyOn(configuracionService, 'getConfiguracion').mockResolvedValue(config)
    const disponibles: SlotResponse[] = [{ hora_inicio: '09:00', hora_fin: '09:30', disponible: true }]
    vi.spyOn(turnoService, 'getDisponibilidad').mockResolvedValue(disponibles)
    renderPage()

    expect(await screen.findByText(/1 disponibles/i)).toBeInTheDocument()
    expect(screen.getByText(/1 ocupados/i)).toBeInTheDocument()
  })

  it('opens the AppointmentModal when clicking Agendar on a slot', async () => {
    vi.spyOn(configuracionService, 'getConfiguracion').mockResolvedValue(config)
    vi.spyOn(turnoService, 'getDisponibilidad').mockResolvedValue([
      { hora_inicio: '09:00', hora_fin: '09:30', disponible: true },
    ])
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /agendar/i }))
    expect(screen.getByRole('heading', { name: 'Nuevo turno' })).toBeInTheDocument()
  })

  it('refetches the slots after successfully agendando a turno', async () => {
    vi.spyOn(configuracionService, 'getConfiguracion').mockResolvedValue(config)
    const getDisponibilidadSpy = vi
      .spyOn(turnoService, 'getDisponibilidad')
      .mockResolvedValue([{ hora_inicio: '09:00', hora_fin: '09:30', disponible: true }])
    const reservado: Turno = {
      id: 10,
      fecha: '2026-08-19',
      hora_inicio: '09:00',
      hora_fin: '09:30',
      estado: 'RESERVADO_TEMPORAL',
      profesional_id: 1,
      paciente_id: null,
      google_event_id: null,
      creado_en: '2026-08-19T00:00:00Z',
    }
    vi.spyOn(turnoService, 'crearReserva').mockResolvedValue(reservado)
    vi.spyOn(turnoService, 'confirmarTurno').mockResolvedValue({ ...reservado, estado: 'CONFIRMADO', paciente_id: 5 })

    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /agendar/i }))
    await user.type(screen.getByLabelText(/^dni$/i), '12345678')
    await user.type(screen.getByLabelText(/nombre/i), 'Juan')
    await user.type(screen.getByLabelText(/apellido/i), 'Pérez')
    await user.type(screen.getByLabelText(/teléfono/i), '555-0001')
    await user.click(screen.getByRole('button', { name: /confirmar turno/i }))

    await vi.waitFor(() => expect(screen.queryByRole('heading', { name: 'Nuevo turno' })).not.toBeInTheDocument())
    expect(getDisponibilidadSpy.mock.calls.length).toBeGreaterThan(1)
  })
})
