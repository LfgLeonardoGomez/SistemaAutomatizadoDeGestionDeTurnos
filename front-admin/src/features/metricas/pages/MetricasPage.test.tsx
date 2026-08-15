import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MetricasPage from './MetricasPage'
import * as metricasService from '../services/metricasService'
import type { GlobalMetrics } from '../../../shared/types'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MetricasPage />
    </QueryClientProvider>,
  )
}

const baseMetrics: GlobalMetrics = {
  total_profesionales: 142,
  profesionales_activos: 128,
  profesionales_inactivos: 14,
  total_turnos: 3482,
  turnos_hoy: 214,
  turnos_confirmados_30d: 2840,
  turnos_cancelados_30d: 642,
  total_pacientes: 8912,
  tasa_confirmacion_30d: 0.815,
  tasa_cancelacion_30d: 0.226,
}

describe('MetricasPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a loading skeleton while fetching', () => {
    vi.spyOn(metricasService, 'getGlobalMetrics').mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByRole('status', { name: /cargando/i })).toBeInTheDocument()
  })

  it('renders all 10 KPIs once loaded', async () => {
    vi.spyOn(metricasService, 'getGlobalMetrics').mockResolvedValue(baseMetrics)
    renderPage()

    expect(await screen.findByText('142')).toBeInTheDocument()
    expect(screen.getByText('128')).toBeInTheDocument()
    expect(screen.getByText('14')).toBeInTheDocument()
    expect(screen.getByText('3.482')).toBeInTheDocument()
    expect(screen.getByText('214')).toBeInTheDocument()
    expect(screen.getByText('2.840')).toBeInTheDocument()
    expect(screen.getByText('642')).toBeInTheDocument()
    expect(screen.getByText('8.912')).toBeInTheDocument()
    expect(screen.getByText('81.5%')).toBeInTheDocument()
    expect(screen.getByText('22.6%')).toBeInTheDocument()
  })

  it('marks "Tasa cancelación 30d" as an alert when above 20%', async () => {
    vi.spyOn(metricasService, 'getGlobalMetrics').mockResolvedValue(baseMetrics)
    renderPage()
    await screen.findByText('22.6%')
    expect(screen.getByText('ALERTA')).toBeInTheDocument()
  })

  it('does not mark the cancellation rate as an alert when 20% or below', async () => {
    vi.spyOn(metricasService, 'getGlobalMetrics').mockResolvedValue({
      ...baseMetrics,
      tasa_cancelacion_30d: 0.15,
    })
    renderPage()
    await screen.findByText('15.0%')
    expect(screen.queryByText('ALERTA')).not.toBeInTheDocument()
  })
})
