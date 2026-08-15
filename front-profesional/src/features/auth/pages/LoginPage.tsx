import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { Input } from '../../../shared/components/ui/Input'
import { Button } from '../../../shared/components/ui/Button'
import { useLogin } from '../hooks/useLogin'

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
  const [showPassword, setShowPassword] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) })
  const { mutate, isPending, isSuccess, isError, error } = useLogin()

  useEffect(() => {
    if (isSuccess) {
      navigate('/', { replace: true })
    }
  }, [isSuccess, navigate])

  return (
    <div className="w-full max-w-sm rounded-xl border border-outline-variant bg-surface-container-lowest p-8 shadow-sm">
      <h1 className="mb-1 text-headline-lg font-semibold">Bienvenido</h1>
      <p className="mb-6 text-body-md text-on-surface-variant">Panel del Profesional</p>
      <form onSubmit={handleSubmit((values) => mutate(values))} className="flex flex-col gap-4" noValidate>
        <Input
          label="Email"
          type="email"
          autoComplete="username"
          placeholder="dr@consultorio.com"
          error={errors.email?.message}
          {...register('email')}
        />
        <div className="relative">
          <Input
            label="Contraseña"
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            error={errors.password?.message}
            {...register('password')}
          />
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
            className="absolute right-3 top-8 text-on-surface-variant hover:text-on-surface"
          >
            <span className="material-symbols-outlined" aria-hidden="true">
              {showPassword ? 'visibility_off' : 'visibility'}
            </span>
          </button>
        </div>
        {isError && (
          <p role="alert" className="rounded-lg bg-error-container px-3 py-2 text-label-md text-error">
            {getErrorMessage(error)}
          </p>
        )}
        <Button type="submit" loading={isPending} className="w-full">
          Iniciar Sesión
        </Button>
      </form>
    </div>
  )
}
