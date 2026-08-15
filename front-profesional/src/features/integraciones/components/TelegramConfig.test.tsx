import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TelegramConfig } from './TelegramConfig'
import * as integracionesService from '../services/integracionesService'

function renderCard(hasTelegram: boolean) {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <TelegramConfig hasTelegram={hasTelegram} />
    </QueryClientProvider>,
  )
}

describe('TelegramConfig', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows "Conectado" when hasTelegram is true', () => {
    renderCard(true)
    expect(screen.getByText('Conectado')).toBeInTheDocument()
  })

  it('shows "Desconectado" when hasTelegram is false', () => {
    renderCard(false)
    expect(screen.getByText('Desconectado')).toBeInTheDocument()
  })

  it('disables the save button until a token is typed', async () => {
    const user = userEvent.setup()
    renderCard(false)

    expect(screen.getByRole('button', { name: /guardar token/i })).toBeDisabled()
    await user.type(screen.getByLabelText(/token del bot/i), 'abc123')
    expect(screen.getByRole('button', { name: /guardar token/i })).toBeEnabled()
  })

  it('saves the token via updateIntegraciones', async () => {
    const updateSpy = vi.spyOn(integracionesService, 'updateIntegraciones').mockResolvedValue({
      has_telegram: true,
      has_google: false,
      google_calendar_id: 'primary',
    })
    const user = userEvent.setup()
    renderCard(false)

    await user.type(screen.getByLabelText(/token del bot/i), 'abc123')
    await user.click(screen.getByRole('button', { name: /guardar token/i }))

    await vi.waitFor(() => expect(updateSpy).toHaveBeenCalledWith({ telegram_bot_token: 'abc123' }, expect.anything()))
  })
})
