import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useAdminLogin } from './useAdminLogin'
import { useAuthStore } from '../../../shared/hooks/useAuth'
import * as authService from '../services/authService'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useAdminLogin', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
    vi.restoreAllMocks()
  })

  it('stores the token on successful login', async () => {
    vi.spyOn(authService, 'adminLogin').mockResolvedValue({
      access_token: 'jwt-token',
      token_type: 'bearer',
    })

    const { result } = renderHook(() => useAdminLogin(), { wrapper })
    result.current.mutate({ email: 'admin@test.com', password: 'admin1234' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(useAuthStore.getState().token).toBe('jwt-token')
  })

  it('does not store a token when login fails', async () => {
    vi.spyOn(authService, 'adminLogin').mockRejectedValue(new Error('401'))

    const { result } = renderHook(() => useAdminLogin(), { wrapper })
    result.current.mutate({ email: 'admin@test.com', password: 'wrong' })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(useAuthStore.getState().token).toBeNull()
  })
})
