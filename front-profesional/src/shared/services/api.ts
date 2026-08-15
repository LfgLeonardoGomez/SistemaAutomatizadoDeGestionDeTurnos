import axios from 'axios'
import { useAuthStore } from '../hooks/useAuth'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clearing the store (not window.location.href) so ProtectedRoute reacts
      // declaratively - keeps this a real SPA navigation, and is what makes
      // this behavior unit-testable (jsdom has no real navigation).
      useAuthStore.getState().logout()
    }
    return Promise.reject(error)
  },
)
