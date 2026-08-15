import { api } from '../../../shared/services/api'
import type { LoginRequest, LoginResponse } from '../../../shared/types'

export function login(credentials: LoginRequest) {
  return api.post<LoginResponse>('/auth/login', credentials).then((res) => res.data)
}
