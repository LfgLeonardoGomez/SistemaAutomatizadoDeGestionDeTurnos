import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ProfesionalDetailPage from './ProfesionalDetailPage'
import * as profesionalService from '../services/profesionalService'
import type { ProfesionalAdminResponse } from '../../../shared/types'

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/profesionales/:id" element={<ProfesionalDetailPage />} />
          <Route path="/" element={<div>Listado de profesionales</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ProfesionalDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a loading skeleton while fetching', () => {
    vi.spyOn(profesionalService, 'getProfesional').mockReturnValue(new Promise(() => {}))
    renderAt('/profesionales/9021')
    expect(screen.getByRole('status', { name: /cargando/i })).toBeInTheDocument()
  })

  it('renders the profesional data on success', async () => {
    const profesional: ProfesionalAdminResponse = {
      id: 9021,
      nombre: 'Dr. Ricardo Mendoza',
      especialidad: 'Odontología general',
      email: 'ricardo@clinica.com',
      is_active: true,
      creado_en: '2026-01-15T00:00:00Z',
    }
    vi.spyOn(profesionalService, 'getProfesional').mockResolvedValue(profesional)
    renderAt('/profesionales/9021')

    expect(await screen.findByText('Dr. Ricardo Mendoza')).toBeInTheDocument()
    expect(screen.getByText('Odontología general')).toBeInTheDocument()
    expect(screen.getByText('ricardo@clinica.com')).toBeInTheDocument()
    expect(screen.getByText('Activo')).toBeInTheDocument()
  })

  it('calls getProfesional with the id from the route params', async () => {
    const spy = vi
      .spyOn(profesionalService, 'getProfesional')
      .mockResolvedValue({
        id: 9021,
        nombre: 'Dr. Ricardo Mendoza',
        especialidad: 'Odontología general',
        email: 'ricardo@clinica.com',
        is_active: true,
        creado_en: '2026-01-15T00:00:00Z',
      })
    renderAt('/profesionales/9021')
    await screen.findByText('Dr. Ricardo Mendoza')
    expect(spy).toHaveBeenCalledWith(9021)
  })

  it('shows a not-found message and a link back to the list on 404', async () => {
    vi.spyOn(profesionalService, 'getProfesional').mockRejectedValue({
      response: { status: 404 },
    })
    renderAt('/profesionales/9999')

    expect(await screen.findByText(/profesional no encontrado/i)).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /volver al listado/i })
    expect(link).toHaveAttribute('href', '/')
  })
})
