import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppointmentModal } from './AppointmentModal'
import * as turnoService from '../services/turnoService'
import * as pacienteService from '../../pacientes/services/pacienteService'
import type { Turno } from '../../../shared/types'

function renderModal(onSuccess = vi.fn(), onClose = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <AppointmentModal isOpen fecha="2026-08-19" horaInicio="09:00" onClose={onClose} onSuccess={onSuccess} />
    </QueryClientProvider>,
  )
}

describe('AppointmentModal', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows the selected date and time', () => {
    renderModal()
    expect(screen.getByText(/09:00/)).toBeInTheDocument()
  })

  it('prefills nombre/apellido/telefono when searching an existing DNI', async () => {
    vi.spyOn(pacienteService, 'buscarPorDni').mockResolvedValue({
      id: 5,
      nombre: 'Juan',
      apellido: 'Pérez',
      dni: '12345678',
      telefono: '555-0001',
    })
    const user = userEvent.setup()
    renderModal()

    await user.type(screen.getByLabelText(/^dni$/i), '12345678')
    await user.click(screen.getByRole('button', { name: /buscar/i }))

    expect(await screen.findByDisplayValue('Juan')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Pérez')).toBeInTheDocument()
    expect(screen.getByDisplayValue('555-0001')).toBeInTheDocument()
  })

  it('shows validation errors when submitting empty fields', async () => {
    const user = userEvent.setup()
    renderModal()

    await user.click(screen.getByRole('button', { name: /confirmar turno/i }))

    expect(await screen.findAllByRole('alert')).toHaveLength(4)
  })

  it('creates and confirms the turno, then calls onSuccess', async () => {
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
    const confirmado: Turno = { ...reservado, estado: 'CONFIRMADO', paciente_id: 5 }
    vi.spyOn(turnoService, 'crearReserva').mockResolvedValue(reservado)
    vi.spyOn(turnoService, 'confirmarTurno').mockResolvedValue(confirmado)
    const onSuccess = vi.fn()
    const user = userEvent.setup()
    renderModal(onSuccess)

    await user.type(screen.getByLabelText(/^dni$/i), '12345678')
    await user.type(screen.getByLabelText(/nombre/i), 'Juan')
    await user.type(screen.getByLabelText(/apellido/i), 'Pérez')
    await user.type(screen.getByLabelText(/teléfono/i), '555-0001')
    await user.click(screen.getByRole('button', { name: /confirmar turno/i }))

    await vi.waitFor(() => expect(onSuccess).toHaveBeenCalledWith(confirmado))
  })

  it('shows a 409 error (paciente con turno activo) without closing the modal', async () => {
    vi.spyOn(turnoService, 'crearReserva').mockRejectedValue({
      response: { status: 409, data: { detail: 'El paciente ya tiene un turno activo' } },
    })
    const onClose = vi.fn()
    const user = userEvent.setup()
    renderModal(vi.fn(), onClose)

    await user.type(screen.getByLabelText(/^dni$/i), '12345678')
    await user.type(screen.getByLabelText(/nombre/i), 'Juan')
    await user.type(screen.getByLabelText(/apellido/i), 'Pérez')
    await user.type(screen.getByLabelText(/teléfono/i), '555-0001')
    await user.click(screen.getByRole('button', { name: /confirmar turno/i }))

    expect(await screen.findByText(/el paciente ya tiene un turno activo/i)).toBeInTheDocument()
    expect(onClose).not.toHaveBeenCalled()
  })
})
