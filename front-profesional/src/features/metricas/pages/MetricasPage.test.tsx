import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MetricasPage from './MetricasPage'
import * as metricasService from '../services/metricasService'
import type { Metricas } from '../../../shared/types'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MetricasPage />
    </QueryClientProvider>,
  )
}

describe('MetricasPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a loading skeleton while fetching', () => {
    vi.spyOn(metricasService, 'getMetricas').mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByRole('status', { name: /cargando/i })).toBeInTheDocument()
  })

  it('renders the 3 KPIs once loaded', async () => {
    const data: Metricas = { turnos_hoy: 5, tasa_confirmacion_30d: 0.82, tasa_cancelacion_30d: 0.1 }
    vi.spyOn(metricasService, 'getMetricas').mockResolvedValue(data)
    renderPage()

    expect(await screen.findByText('5')).toBeInTheDocument()
    expect(screen.getByText('82.0%')).toBeInTheDocument()
    expect(screen.getByText('10.0%')).toBeInTheDocument()
  })

  it('marks tasa cancelación as alert when above 20%', async () => {
    const data: Metricas = { turnos_hoy: 5, tasa_confirmacion_30d: 0.6, tasa_cancelacion_30d: 0.25 }
    vi.spyOn(metricasService, 'getMetricas').mockResolvedValue(data)
    renderPage()

    await screen.findByText('25.0%')
    expect(screen.getByText('ALERTA')).toBeInTheDocument()
  })

  it('does not mark tasa cancelación as alert at 20% or below', async () => {
    const data: Metricas = { turnos_hoy: 5, tasa_confirmacion_30d: 0.6, tasa_cancelacion_30d: 0.2 }
    vi.spyOn(metricasService, 'getMetricas').mockResolvedValue(data)
    renderPage()

    await screen.findByText('20.0%')
    expect(screen.queryByText('ALERTA')).not.toBeInTheDocument()
  })
})
