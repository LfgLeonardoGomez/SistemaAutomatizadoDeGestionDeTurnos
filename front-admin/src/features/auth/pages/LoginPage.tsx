import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { Input } from '../../../shared/components/ui/Input'
import { Button } from '../../../shared/components/ui/Button'
import { useAdminLogin } from '../hooks/useAdminLogin'

const loginSchema = z.object({
  email: z.string().min(1, 'El email es requerido').email('Email inválido'),
  password: z.string().min(1, 'La contraseña es requerida'),
})

type LoginFormValues = z.infer<typeof loginSchema>

function getErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    if (response?.data?.detail) return response.data.detail
  }
  return 'No se pudo iniciar sesión. Intentá de nuevo.'
}

export default function LoginPage() {
  const navigate = useNavigate()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) })
  const { mutate, isPending, isSuccess, isError, error } = useAdminLogin()

  useEffect(() => {
    if (isSuccess) {
      navigate('/', { replace: true })
    }
  }, [isSuccess, navigate])

  return (
    <div className="w-full max-w-sm rounded-xl border border-outline-variant bg-surface-container-lowest p-8 shadow-sm">
      <h1 className="mb-6 text-headline-sm font-semibold">Iniciar sesión</h1>
      <form
        onSubmit={handleSubmit((values) => mutate(values))}
        className="flex flex-col gap-4"
        noValidate
      >
        <Input
          label="Email"
          type="email"
          autoComplete="username"
          error={errors.email?.message}
          {...register('email')}
        />
        <Input
          label="Contraseña"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register('password')}
        />
        {isError && (
          <p role="alert" className="rounded-lg bg-error-container px-3 py-2 text-label-md text-error">
            {getErrorMessage(error)}
          </p>
        )}
        <Button type="submit" loading={isPending}>
          Iniciar sesión
        </Button>
      </form>
    </div>
  )
}
