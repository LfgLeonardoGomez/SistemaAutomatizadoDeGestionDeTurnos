import { beforeEach, describe, expect, it } from 'vitest'
import { useAuthStore } from './useAuth'

describe('useAuthStore', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.getState().logout()
  })

  it('starts with no token', () => {
    expect(useAuthStore.getState().token).toBeNull()
  })

  it('setToken stores the token and persists it to localStorage', () => {
    useAuthStore.getState().setToken('abc123')
    expect(useAuthStore.getState().token).toBe('abc123')

    const persisted = JSON.parse(localStorage.getItem('sagt-admin-auth') ?? '{}')
    expect(persisted.state.token).toBe('abc123')
  })

  it('logout clears the token', () => {
    useAuthStore.getState().setToken('abc123')
    useAuthStore.getState().logout()
    expect(useAuthStore.getState().token).toBeNull()
  })
})
