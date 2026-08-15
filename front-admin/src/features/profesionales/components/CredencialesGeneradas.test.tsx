import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CredencialesGeneradas } from './CredencialesGeneradas'

describe('CredencialesGeneradas', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows the api_key and telegram_secret_token with a one-time warning', () => {
    render(
      <CredencialesGeneradas apiKey="pk_live_abc123" telegramSecretToken="tg_secret_xyz" onConfirm={() => {}} />,
    )
    expect(screen.getByDisplayValue('pk_live_abc123')).toBeInTheDocument()
    expect(screen.getByDisplayValue('tg_secret_xyz')).toBeInTheDocument()
    expect(screen.getByText(/una sola vez/i)).toBeInTheDocument()
  })

  it('has no close (X) button', () => {
    render(
      <CredencialesGeneradas apiKey="pk_live_abc123" telegramSecretToken="tg_secret_xyz" onConfirm={() => {}} />,
    )
    expect(screen.queryByRole('button', { name: /cerrar/i })).not.toBeInTheDocument()
  })

  it('pressing Escape does not confirm/close', async () => {
    const onConfirm = vi.fn()
    const user = userEvent.setup()
    render(
      <CredencialesGeneradas apiKey="pk_live_abc123" telegramSecretToken="tg_secret_xyz" onConfirm={onConfirm} />,
    )
    await user.keyboard('{Escape}')
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('copies the api_key to the clipboard and shows feedback', async () => {
    const user = userEvent.setup()
    // userEvent.setup() installs its own navigator.clipboard stub, so ours must be
    // defined after setup() runs or userEvent's stub wins and our mock never gets called.
    const writeTextMock = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: writeTextMock },
      configurable: true,
    })
    render(
      <CredencialesGeneradas apiKey="pk_live_abc123" telegramSecretToken="tg_secret_xyz" onConfirm={() => {}} />,
    )
    const [copyApiKeyButton] = screen.getAllByRole('button', { name: /copiar/i })
    await user.click(copyApiKeyButton)

    expect(writeTextMock).toHaveBeenCalledWith('pk_live_abc123')
    expect(await screen.findByText('¡Copiado!')).toBeInTheDocument()
  })

  it('calls onConfirm only when clicking "Ya copié las credenciales"', async () => {
    const onConfirm = vi.fn()
    const user = userEvent.setup()
    render(
      <CredencialesGeneradas apiKey="pk_live_abc123" telegramSecretToken="tg_secret_xyz" onConfirm={onConfirm} />,
    )
    await user.click(screen.getByRole('button', { name: /ya copié las credenciales/i }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('registers a beforeunload guard while mounted and removes it on unmount', () => {
    const addSpy = vi.spyOn(window, 'addEventListener')
    const removeSpy = vi.spyOn(window, 'removeEventListener')

    const { unmount } = render(
      <CredencialesGeneradas apiKey="pk_live_abc123" telegramSecretToken="tg_secret_xyz" onConfirm={() => {}} />,
    )
    expect(addSpy).toHaveBeenCalledWith('beforeunload', expect.any(Function))

    const handler = addSpy.mock.calls.find(([event]) => event === 'beforeunload')?.[1] as EventListener
    const fakeEvent = { preventDefault: vi.fn(), returnValue: '' } as unknown as BeforeUnloadEvent
    handler(fakeEvent)
    expect(fakeEvent.preventDefault).toHaveBeenCalled()

    unmount()
    expect(removeSpy).toHaveBeenCalledWith('beforeunload', expect.any(Function))
  })
})
