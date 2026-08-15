import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { routes } from './router'
import { useAuthStore } from '../shared/hooks/useAuth'
import * as profesionalService from '../features/profesionales/services/profesionalService'
import * as metricasService from '../features/metricas/services/metricasService'

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('router', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
    vi.spyOn(profesionalService, 'listProfesionales').mockResolvedValue([])
    vi.spyOn(profesionalService, 'getProfesional').mockResolvedValue({
      id: 42,
      nombre: 'Dr. Ricardo Mendoza',
      especialidad: 'Odontología general',
      email: 'ricardo@clinica.com',
      is_active: true,
      creado_en: '2026-01-01T00:00:00Z',
    })
    vi.spyOn(metricasService, 'getGlobalMetrics').mockResolvedValue({
      total_profesionales: 1,
      profesionales_activos: 1,
      profesionales_inactivos: 0,
      total_turnos: 1,
      turnos_hoy: 1,
      turnos_confirmados_30d: 1,
      turnos_cancelados_30d: 0,
      total_pacientes: 1,
      tasa_confirmacion_30d: 1,
      tasa_cancelacion_30d: 0,
    })
  })

  it('renders the login page inside AuthLayout at /login', async () => {
    renderAt('/login')
    expect(await screen.findByRole('heading', { name: /iniciar sesión/i })).toBeInTheDocument()
    expect(screen.getByText(/panel de administración/i)).toBeInTheDocument()
  })

  it('redirects to /login when visiting a protected route without a token', async () => {
    renderAt('/')
    expect(await screen.findByRole('heading', { name: /iniciar sesión/i })).toBeInTheDocument()
  })

  it('renders the profesionales list at / inside AppLayout when authenticated', async () => {
    useAuthStore.getState().setToken('valid-token')
    renderAt('/')
    // Longer timeout: this is the first test to touch the lazy-loaded ProfesionalesListPage
    // chunk (which pulls in date-fns), so Vite's cold on-demand transform can exceed the
    // default 1000ms findBy timeout. Not a hang - see router-test-full.log investigation.
    expect(
      await screen.findByRole('heading', { name: /profesionales/i }, { timeout: 5000 }),
    ).toBeInTheDocument()
    expect(screen.getByText('Admin Portal')).toBeInTheDocument()
  })

  it('renders the profesional detail page at /profesionales/:id when authenticated', async () => {
    useAuthStore.getState().setToken('valid-token')
    renderAt('/profesionales/42')
    // Same cold-transform reasoning as the profesionales-list test above.
    expect(
      await screen.findByRole('heading', { name: /detalle de profesional/i }, { timeout: 5000 }),
    ).toBeInTheDocument()
  })

  it('renders the metricas page at /metricas when authenticated', async () => {
    useAuthStore.getState().setToken('valid-token')
    renderAt('/metricas')
    expect(
      await screen.findByRole('heading', { name: /métricas globales/i }, { timeout: 5000 }),
    ).toBeInTheDocument()
  })

  it('renders the 404 page for an unknown route', async () => {
    renderAt('/esto-no-existe')
    expect(await screen.findByText('404')).toBeInTheDocument()
  })
})
