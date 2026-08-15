import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import IntegracionesPage from './IntegracionesPage'
import * as integracionesService from '../services/integracionesService'
import type { Integraciones } from '../../../shared/types'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <IntegracionesPage />
    </QueryClientProvider>,
  )
}

describe('IntegracionesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a loading skeleton while fetching', () => {
    vi.spyOn(integracionesService, 'getIntegraciones').mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByRole('status', { name: /cargando/i })).toBeInTheDocument()
  })

  it('renders both integration cards once loaded', async () => {
    const data: Integraciones = { has_telegram: true, has_google: false, google_calendar_id: 'primary' }
    vi.spyOn(integracionesService, 'getIntegraciones').mockResolvedValue(data)
    renderPage()

    expect(await screen.findByText('Telegram')).toBeInTheDocument()
    expect(screen.getByText('Google Calendar')).toBeInTheDocument()
    expect(screen.getByDisplayValue('primary')).toBeInTheDocument()
  })

  it('shows an HTTPS warning when the page is not served over https', async () => {
    vi.stubGlobal('location', { ...window.location, protocol: 'http:' })
    vi.spyOn(integracionesService, 'getIntegraciones').mockResolvedValue({
      has_telegram: false,
      has_google: false,
      google_calendar_id: 'primary',
    })
    renderPage()

    expect(await screen.findByText(/necesitás https/i)).toBeInTheDocument()
  })

  it('does not show the HTTPS warning when served over https', async () => {
    vi.stubGlobal('location', { ...window.location, protocol: 'https:' })
    vi.spyOn(integracionesService, 'getIntegraciones').mockResolvedValue({
      has_telegram: false,
      has_google: false,
      google_calendar_id: 'primary',
    })
    renderPage()

    await screen.findByText('Telegram')
    expect(screen.queryByText(/necesitás https/i)).not.toBeInTheDocument()
  })
})
