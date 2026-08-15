import { beforeEach, describe, expect, it } from 'vitest'
import type { InternalAxiosRequestConfig } from 'axios'
import { api } from './api'
import { useAuthStore } from '../hooks/useAuth'

// axios does not publicly type the internal `handlers` array, but exposes it at runtime.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const interceptors = api.interceptors as any

describe('api client', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
    window.history.pushState({}, '', '/')
  })

  it('attaches the Authorization header when a token is present', () => {
    useAuthStore.getState().setToken('my-token')
    const config = { headers: {} } as InternalAxiosRequestConfig
    const requestInterceptor = interceptors.request.handlers[0].fulfilled
    const result = requestInterceptor(config) as InternalAxiosRequestConfig
    expect(result.headers.Authorization).toBe('Bearer my-token')
  })

  it('does not attach an Authorization header when there is no token', () => {
    const config = { headers: {} } as InternalAxiosRequestConfig
    const requestInterceptor = interceptors.request.handlers[0].fulfilled
    const result = requestInterceptor(config) as InternalAxiosRequestConfig
    expect(result.headers.Authorization).toBeUndefined()
  })

  it('logs out on a 401 response', async () => {
    useAuthStore.getState().setToken('my-token')
    const responseErrorInterceptor = interceptors.response.handlers[0].rejected
    await expect(responseErrorInterceptor({ response: { status: 401 } })).rejects.toBeDefined()
    expect(useAuthStore.getState().token).toBeNull()
  })

  it('does not log out on a non-401 error', async () => {
    useAuthStore.getState().setToken('my-token')
    const responseErrorInterceptor = interceptors.response.handlers[0].rejected
    await expect(responseErrorInterceptor({ response: { status: 500 } })).rejects.toBeDefined()
    expect(useAuthStore.getState().token).toBe('my-token')
  })
})
