import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { routes } from './router'
import { useAuthStore } from '../shared/hooks/useAuth'
import * as turnosHoyService from '../features/dashboard/services/turnosHoyService'
import * as turnoService from '../features/agenda/services/turnoService'
import * as configuracionService from '../features/configuracion/services/configuracionService'
import * as pacienteService from '../features/pacientes/services/pacienteService'
import * as metricasService from '../features/metricas/services/metricasService'
import * as integracionesService from '../features/integraciones/services/integracionesService'

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
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
    vi.spyOn(turnosHoyService, 'getTurnosHoy').mockResolvedValue([])
    vi.spyOn(configuracionService, 'getConfiguracion').mockResolvedValue({
      horario_inicio: '09:00',
      horario_fin: '17:00',
      dias_atencion: ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'],
      duracion_turno: 30,
      especialidad: 'Odontología general',
    })
    vi.spyOn(turnoService, 'getDisponibilidad').mockResolvedValue([])
    vi.spyOn(metricasService, 'getMetricas').mockResolvedValue({
      turnos_hoy: 0,
      tasa_confirmacion_30d: 0,
      tasa_cancelacion_30d: 0,
    })
    vi.spyOn(integracionesService, 'getIntegraciones').mockResolvedValue({
      has_telegram: false,
      has_google: false,
      google_calendar_id: 'primary',
    })
    vi.spyOn(pacienteService, 'listPacientes').mockResolvedValue([])
    vi.spyOn(pacienteService, 'getPaciente').mockResolvedValue({
      id: 7,
      nombre: 'Juan',
      apellido: 'Pérez',
      dni: '12345678',
      telefono: '555-0001',
      creado_en: '2026-01-01T00:00:00Z',
      turnos: [],
    })
  })

  it('renders the login page inside AuthLayout at /login', async () => {
    renderAt('/login')
    // First test to touch the lazy-loaded LoginPage chunk (pulls in RHF+Zod) -
    // cold Vite transform can exceed the default 1000ms findBy timeout.
    expect(await screen.findByRole('heading', { name: /bienvenido/i }, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.getAllByText(/panel del profesional/i).length).toBeGreaterThan(0)
  })

  it('redirects to /login when visiting a protected route without a token', async () => {
    renderAt('/')
    expect(await screen.findByRole('heading', { name: /bienvenido/i }, { timeout: 5000 })).toBeInTheDocument()
  })

  it('renders the dashboard at / inside AppLayout when authenticated', async () => {
    useAuthStore.getState().setToken('valid-token')
    renderAt('/')
    expect(await screen.findByRole('heading', { name: /turnos de hoy/i }, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.getByText('SG Turnos')).toBeInTheDocument()
  })

  it('renders the agenda page at /agenda when authenticated', async () => {
    useAuthStore.getState().setToken('valid-token')
    renderAt('/agenda')
    // Agenda is the heaviest lazy chunk (date-fns/locale + several sub-components) -
    // under full-suite contention the cold transform can exceed 5000ms, so this
    // needs more headroom than the other routes (see vite.config.ts testTimeout).
    expect(await screen.findByRole('heading', { name: /^agenda$/i }, { timeout: 9000 })).toBeInTheDocument()
  })

  it('renders the pacientes list at /pacientes when authenticated', async () => {
    useAuthStore.getState().setToken('valid-token')
    renderAt('/pacientes')
    expect(await screen.findByRole('heading', { name: /^pacientes$/i }, { timeout: 5000 })).toBeInTheDocument()
  })

  it('renders the paciente detail page at /pacientes/:id when authenticated', async () => {
    useAuthStore.getState().setToken('valid-token')
    renderAt('/pacientes/7')
    expect(
      await screen.findByRole('heading', { name: /detalle de paciente/i }, { timeout: 5000 }),
    ).toBeInTheDocument()
  })

  it('renders the configuracion page at /configuracion when authenticated', async () => {
    useAuthStore.getState().setToken('valid-token')
    renderAt('/configuracion')
    expect(
      await screen.findByRole('heading', { name: /^configuración$/i }, { timeout: 5000 }),
    ).toBeInTheDocument()
  })

  it('renders the metricas page at /metricas when authenticated', async () => {
    useAuthStore.getState().setToken('valid-token')
    renderAt('/metricas')
    expect(await screen.findByRole('heading', { name: /^métricas$/i }, { timeout: 5000 })).toBeInTheDocument()
  })

  it('renders the integraciones page at /integraciones when authenticated', async () => {
    useAuthStore.getState().setToken('valid-token')
    renderAt('/integraciones')
    expect(
      await screen.findByRole('heading', { name: /^integraciones$/i }, { timeout: 5000 }),
    ).toBeInTheDocument()
  })

  it('renders the 404 page for an unknown route', async () => {
    renderAt('/esto-no-existe')
    expect(await screen.findByText('404')).toBeInTheDocument()
  })
})
