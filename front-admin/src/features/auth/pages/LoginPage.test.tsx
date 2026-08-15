import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import LoginPage from './LoginPage'
import { useAuthStore } from '../../../shared/hooks/useAuth'
import * as authService from '../services/authService'

function renderLoginPage() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  const router = createMemoryRouter(
    [
      { path: '/login', element: <LoginPage /> },
      { path: '/', element: <div>Home protegido</div> },
    ],
    { initialEntries: ['/login'] },
  )
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
    vi.restoreAllMocks()
  })

  it('shows validation errors when submitting empty fields', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    await user.click(screen.getByRole('button', { name: /iniciar sesión/i }))

    expect(await screen.findAllByRole('alert')).toHaveLength(2)
  })

  it('shows an error message when credentials are invalid (401)', async () => {
    vi.spyOn(authService, 'adminLogin').mockRejectedValue({
      response: { status: 401, data: { detail: 'Email o contraseña incorrectos' } },
    })
    const user = userEvent.setup()
    renderLoginPage()

    await user.type(screen.getByLabelText(/email/i), 'admin@test.com')
    await user.type(screen.getByLabelText(/contraseña/i), 'wrongpassword')
    await user.click(screen.getByRole('button', { name: /iniciar sesión/i }))

    expect(await screen.findByText(/email o contraseña incorrectos/i)).toBeInTheDocument()
  })

  it('navigates to / after a successful login', async () => {
    vi.spyOn(authService, 'adminLogin').mockResolvedValue({
      access_token: 'jwt-token',
      token_type: 'bearer',
    })
    const user = userEvent.setup()
    renderLoginPage()

    await user.type(screen.getByLabelText(/email/i), 'admin@test.com')
    await user.type(screen.getByLabelText(/contraseña/i), 'admin1234')
    await user.click(screen.getByRole('button', { name: /iniciar sesión/i }))

    expect(await screen.findByText('Home protegido')).toBeInTheDocument()
    expect(useAuthStore.getState().token).toBe('jwt-token')
  })
})
