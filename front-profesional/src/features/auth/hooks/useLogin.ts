import { useMutation } from '@tanstack/react-query'
import { login } from '../services/authService'
import { useAuthStore } from '../../../shared/hooks/useAuth'

export function useLogin() {
  const setToken = useAuthStore((state) => state.setToken)

  return useMutation({
    mutationFn: login,
    onSuccess: (data) => {
      setToken(data.access_token)
    },
  })
}
