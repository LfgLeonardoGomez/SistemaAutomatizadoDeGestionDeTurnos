import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import PacientesListPage from './PacientesListPage'
import * as pacienteService from '../services/pacienteService'
import type { Paciente } from '../../../shared/types'

function buildPacientes(count: number): Paciente[] {
  return Array.from({ length: count }, (_, i) => ({
    id: 100 + i,
    nombre: `Paciente${i}`,
    apellido: `Apellido${i}`,
    dni: `1000000${i}`,
    telefono: `555-000${i}`,
    creado_en: '2026-01-01T00:00:00Z',
  }))
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <PacientesListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('PacientesListPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a loading skeleton while fetching', () => {
    vi.spyOn(pacienteService, 'listPacientes').mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByRole('status', { name: /cargando/i })).toBeInTheDocument()
  })

  it('shows an empty state when there are no pacientes', async () => {
    vi.spyOn(pacienteService, 'listPacientes').mockResolvedValue([])
    renderPage()
    expect(await screen.findByText(/sin pacientes/i)).toBeInTheDocument()
  })

  it('renders the table once loaded', async () => {
    vi.spyOn(pacienteService, 'listPacientes').mockResolvedValue(buildPacientes(2))
    renderPage()
    expect(await screen.findByText('Paciente0 Apellido0')).toBeInTheDocument()
    expect(screen.getByText('Paciente1 Apellido1')).toBeInTheDocument()
  })

  it('filters by name, apellido or dni as the user types', async () => {
    vi.spyOn(pacienteService, 'listPacientes').mockResolvedValue(buildPacientes(2))
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Paciente0 Apellido0')
    await user.type(screen.getByPlaceholderText(/buscar por nombre, apellido o dni/i), '10000001')

    expect(screen.getByText('Paciente1 Apellido1')).toBeInTheDocument()
    expect(screen.queryByText('Paciente0 Apellido0')).not.toBeInTheDocument()
  })
})
