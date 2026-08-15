import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ProfesionalesListPage from './ProfesionalesListPage'
import * as profesionalService from '../services/profesionalService'
import type { ProfesionalAdminResponse, ProfesionalCreateResponse } from '../../../shared/types'

function buildProfesionales(count: number): ProfesionalAdminResponse[] {
  return Array.from({ length: count }, (_, i) => ({
    id: 9000 + i,
    nombre: `Dr. Profesional ${i}`,
    especialidad: 'Odontología general',
    email: `profesional${i}@clinica.com`,
    is_active: true,
    creado_en: '2026-01-01T00:00:00Z',
  }))
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProfesionalesListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ProfesionalesListPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a loading skeleton while fetching', () => {
    vi.spyOn(profesionalService, 'listProfesionales').mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByRole('status', { name: /cargando/i })).toBeInTheDocument()
  })

  it('shows an empty state when there are no profesionales', async () => {
    vi.spyOn(profesionalService, 'listProfesionales').mockResolvedValue([])
    renderPage()
    expect(await screen.findByText(/sin profesionales/i)).toBeInTheDocument()
  })

  it('renders the table once data loads', async () => {
    vi.spyOn(profesionalService, 'listProfesionales').mockResolvedValue(buildProfesionales(3))
    renderPage()
    expect(await screen.findByText('Dr. Profesional 0')).toBeInTheDocument()
    expect(screen.getByText('Dr. Profesional 1')).toBeInTheDocument()
    expect(screen.getByText('Dr. Profesional 2')).toBeInTheDocument()
  })

  it('filters rows client-side by name or email as the user types', async () => {
    vi.spyOn(profesionalService, 'listProfesionales').mockResolvedValue(buildProfesionales(3))
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Dr. Profesional 0')
    await user.type(screen.getByPlaceholderText(/buscar por nombre o email/i), 'profesional1@')

    expect(screen.getByText('Dr. Profesional 1')).toBeInTheDocument()
    expect(screen.queryByText('Dr. Profesional 0')).not.toBeInTheDocument()
    expect(screen.queryByText('Dr. Profesional 2')).not.toBeInTheDocument()
  })

  it('paginates results 10 per page', async () => {
    vi.spyOn(profesionalService, 'listProfesionales').mockResolvedValue(buildProfesionales(15))
    renderPage()

    await screen.findByText('Dr. Profesional 0')
    expect(screen.getByText('Dr. Profesional 9')).toBeInTheDocument()
    expect(screen.queryByText('Dr. Profesional 10')).not.toBeInTheDocument()
    expect(screen.getByText(/mostrando 1 a 10 de 15 profesionales/i)).toBeInTheDocument()

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: '2' }))

    expect(screen.getByText('Dr. Profesional 10')).toBeInTheDocument()
    expect(screen.queryByText('Dr. Profesional 0')).not.toBeInTheDocument()
  })

  it('opens the create modal from the "+ Nuevo profesional" button', async () => {
    vi.spyOn(profesionalService, 'listProfesionales').mockResolvedValue([])
    const user = userEvent.setup()
    renderPage()

    await screen.findByText(/sin profesionales/i)
    await user.click(screen.getByRole('button', { name: /nuevo profesional/i }))

    expect(screen.getByRole('heading', { name: 'Nuevo profesional' })).toBeInTheDocument()
  })

  it('shows the CredencialesGeneradas screen after creating a profesional, then returns to the list', async () => {
    vi.spyOn(profesionalService, 'listProfesionales').mockResolvedValue([])
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
    const user = userEvent.setup()
    renderPage()

    await screen.findByText(/sin profesionales/i)
    await user.click(screen.getByRole('button', { name: /nuevo profesional/i }))
    await user.type(screen.getByLabelText(/nombre completo/i), 'Dr. Alejandro Méndez')
    await user.type(screen.getByLabelText(/correo electrónico/i), 'alejandro@clinica.com')
    await user.type(screen.getByLabelText(/^especialidad/i), 'Ortodoncia')
    await user.type(screen.getByLabelText(/^contraseña$/i), 'password123')
    await user.type(screen.getByLabelText(/confirmar contraseña/i), 'password123')
    await user.click(screen.getByRole('button', { name: /crear profesional/i }))

    expect(await screen.findByText(/profesional creado con éxito/i)).toBeInTheDocument()
    expect(screen.getByDisplayValue('pk_live_abc123')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /ya copié las credenciales/i }))
    expect(screen.queryByText(/profesional creado con éxito/i)).not.toBeInTheDocument()
  })

  it('asks for confirmation before deactivating an active profesional, then calls the mutation', async () => {
    vi.spyOn(profesionalService, 'listProfesionales').mockResolvedValue(buildProfesionales(1))
    const deactivateSpy = vi.spyOn(profesionalService, 'deactivateProfesional').mockResolvedValue({
      ...buildProfesionales(1)[0],
      is_active: false,
    })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Dr. Profesional 0')
    await user.click(screen.getByRole('button', { name: /desactivar/i }))

    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText(/¿estás seguro de desactivar a dr\. profesional 0\?/i)).toBeInTheDocument()

    await user.click(within(dialog).getByRole('button', { name: 'Desactivar' }))
    await vi.waitFor(() => expect(deactivateSpy).toHaveBeenCalledWith(9000))
  })

  it('does not call the mutation when cancelling the confirm dialog', async () => {
    vi.spyOn(profesionalService, 'listProfesionales').mockResolvedValue(buildProfesionales(1))
    const deactivateSpy = vi.spyOn(profesionalService, 'deactivateProfesional')
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Dr. Profesional 0')
    await user.click(screen.getByRole('button', { name: /desactivar/i }))
    await user.click(screen.getByRole('button', { name: /cancelar/i }))

    expect(screen.queryByText(/¿estás seguro/i)).not.toBeInTheDocument()
    expect(deactivateSpy).not.toHaveBeenCalled()
  })
})
