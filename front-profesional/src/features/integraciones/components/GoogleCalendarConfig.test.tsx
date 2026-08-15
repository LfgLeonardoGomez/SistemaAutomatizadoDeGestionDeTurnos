import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { GoogleCalendarConfig } from './GoogleCalendarConfig'
import * as integracionesService from '../services/integracionesService'

function renderCard(hasGoogle: boolean, googleCalendarId = 'primary') {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <GoogleCalendarConfig hasGoogle={hasGoogle} googleCalendarId={googleCalendarId} />
    </QueryClientProvider>,
  )
}

describe('GoogleCalendarConfig', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows "Conectado" when hasGoogle is true', () => {
    renderCard(true)
    expect(screen.getByText('Conectado')).toBeInTheDocument()
  })

  it('shows "Desconectado" when hasGoogle is false', () => {
    renderCard(false)
    expect(screen.getByText('Desconectado')).toBeInTheDocument()
  })

  it('prefills the Calendar ID with the current value', () => {
    renderCard(true, 'mi-consultorio@group.calendar.google.com')
    expect(screen.getByDisplayValue('mi-consultorio@group.calendar.google.com')).toBeInTheDocument()
  })

  it('saves refresh token and calendar id via updateIntegraciones', async () => {
    const updateSpy = vi.spyOn(integracionesService, 'updateIntegraciones').mockResolvedValue({
      has_telegram: false,
      has_google: true,
      google_calendar_id: 'primary',
    })
    const user = userEvent.setup()
    renderCard(false)

    await user.type(screen.getByLabelText(/refresh token/i), 'refresh-abc')
    await user.click(screen.getByRole('button', { name: /^guardar$/i }))

    await vi.waitFor(() =>
      expect(updateSpy).toHaveBeenCalledWith(
        { google_refresh_token: 'refresh-abc', google_calendar_id: 'primary' },
        expect.anything(),
      ),
    )
  })
})
