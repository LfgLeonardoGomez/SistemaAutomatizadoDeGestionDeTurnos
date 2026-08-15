import { useMutation } from '@tanstack/react-query'
import { adminLogin } from '../services/authService'
import { useAuthStore } from '../../../shared/hooks/useAuth'

export function useAdminLogin() {
  const setToken = useAuthStore((state) => state.setToken)

  return useMutation({
    mutationFn: adminLogin,
    onSuccess: (data) => {
      setToken(data.access_token)
    },
  })
}
