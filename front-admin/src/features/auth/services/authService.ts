import { api } from '../../../shared/services/api'
import type { SuperAdminLoginRequest, TokenResponse } from '../../../shared/types'

export function adminLogin(credentials: SuperAdminLoginRequest) {
  return api.post<TokenResponse>('/admin/auth/login', credentials).then((res) => res.data)
}
