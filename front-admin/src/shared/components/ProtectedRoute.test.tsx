import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { ProtectedRoute } from './ProtectedRoute'
import { useAuthStore } from '../hooks/useAuth'

function renderProtected(initialPath: string) {
  const router = createMemoryRouter(
    [
      {
        element: <ProtectedRoute />,
        children: [{ path: '/', element: <div>Contenido protegido</div> }],
      },
      { path: '/login', element: <div>Login page</div> },
    ],
    { initialEntries: [initialPath] },
  )
  return render(<RouterProvider router={router} />)
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
  })

  it('redirects to /login when there is no token', async () => {
    renderProtected('/')
    expect(await screen.findByText('Login page')).toBeInTheDocument()
  })

  it('renders the protected content when a token is present', async () => {
    useAuthStore.getState().setToken('valid-token')
    renderProtected('/')
    expect(await screen.findByText('Contenido protegido')).toBeInTheDocument()
  })
})
