import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '../../../shared/components/ui/Modal'
import { Input } from '../../../shared/components/ui/Input'
import { Button } from '../../../shared/components/ui/Button'
import { useCrearProfesional } from '../hooks/useCrearProfesional'
import type { ProfesionalCreateResponse } from '../../../shared/types'

const createProfesionalSchema = z
  .object({
    nombre: z.string().min(1, 'El nombre es requerido'),
    email: z.string().min(1, 'El email es requerido').email('Email inválido'),
    especialidad: z.string().min(1, 'La especialidad es requerida'),
    password: z.string().min(8, 'La contraseña debe tener al menos 8 caracteres'),
    confirmarPassword: z.string().min(1, 'Confirmá la contraseña'),
  })
  .refine((data) => data.password === data.confirmarPassword, {
    message: 'Las contraseñas no coinciden',
    path: ['confirmarPassword'],
  })

type CreateProfesionalFormValues = z.infer<typeof createProfesionalSchema>

interface CreateProfesionalModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (data: ProfesionalCreateResponse) => void
}

function getErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { status?: number } }).response
    if (response?.status === 409) return 'Ya existe un profesional con ese email'
  }
  return 'No se pudo crear el profesional. Intentá de nuevo.'
}

export function CreateProfesionalModal({ isOpen, onClose, onSuccess }: CreateProfesionalModalProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateProfesionalFormValues>({ resolver: zodResolver(createProfesionalSchema) })
  const { mutate, isPending, isError, error } = useCrearProfesional()

  function handleClose() {
    reset()
    onClose()
  }

  function onSubmit(values: CreateProfesionalFormValues) {
    mutate(
      {
        nombre: values.nombre,
        email: values.email,
        especialidad: values.especialidad,
        password: values.password,
      },
      {
        onSuccess: (data) => {
          reset()
          onSuccess(data)
        },
      },
    )
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Nuevo profesional">
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <Input label="Nombre Completo" error={errors.nombre?.message} {...register('nombre')} />
        <Input
          label="Correo Electrónico"
          type="email"
          error={errors.email?.message}
          {...register('email')}
        />
        <Input label="Especialidad" error={errors.especialidad?.message} {...register('especialidad')} />
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Contraseña"
            type="password"
            error={errors.password?.message}
            {...register('password')}
          />
          <Input
            label="Confirmar Contraseña"
            type="password"
            error={errors.confirmarPassword?.message}
            {...register('confirmarPassword')}
          />
        </div>
        {isError && (
          <p role="alert" className="rounded-lg bg-error-container px-3 py-2 text-label-md text-error">
            {getErrorMessage(error)}
          </p>
        )}
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={handleClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={isPending}>
            Crear profesional
          </Button>
        </div>
      </form>
    </Modal>
  )
}
