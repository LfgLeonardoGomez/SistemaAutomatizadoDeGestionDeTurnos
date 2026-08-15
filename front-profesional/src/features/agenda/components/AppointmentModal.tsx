import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '../../../shared/components/ui/Modal'
import { Input } from '../../../shared/components/ui/Input'
import { Button } from '../../../shared/components/ui/Button'
import { useAgendarTurno } from '../hooks/useAgendarTurno'
import { buscarPorDni } from '../../pacientes/services/pacienteService'
import type { Turno } from '../../../shared/types'

const pacienteSchema = z.object({
  dni: z.string().min(1, 'El DNI es requerido'),
  nombre: z.string().min(1, 'El nombre es requerido'),
  apellido: z.string().min(1, 'El apellido es requerido'),
  telefono: z.string().min(1, 'El teléfono es requerido'),
})

type PacienteFormValues = z.infer<typeof pacienteSchema>

function getErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    if (response?.data?.detail) return response.data.detail
  }
  return 'No se pudo agendar el turno. Intentá de nuevo.'
}

interface AppointmentModalProps {
  isOpen: boolean
  fecha: string
  horaInicio: string
  onClose: () => void
  onSuccess: (turno: Turno) => void
}

export function AppointmentModal({ isOpen, fecha, horaInicio, onClose, onSuccess }: AppointmentModalProps) {
  const [isSearching, setIsSearching] = useState(false)
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<PacienteFormValues>({ resolver: zodResolver(pacienteSchema) })
  const { mutate, isPending, isError, error } = useAgendarTurno()

  function handleClose() {
    reset()
    onClose()
  }

  async function handleBuscar() {
    const dni = watch('dni')
    if (!dni) return
    setIsSearching(true)
    try {
      const paciente = await buscarPorDni(dni)
      if (paciente) {
        setValue('nombre', paciente.nombre)
        setValue('apellido', paciente.apellido)
        setValue('telefono', paciente.telefono)
      }
    } finally {
      setIsSearching(false)
    }
  }

  function onSubmit(values: PacienteFormValues) {
    mutate(
      { fecha, hora_inicio: horaInicio, paciente: values },
      {
        onSuccess: (turno) => {
          reset()
          onSuccess(turno)
        },
      },
    )
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Nuevo turno">
      <p className="mb-4 text-body-md text-on-surface-variant">
        {fecha} · {horaInicio}
      </p>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Input label="DNI" error={errors.dni?.message} {...register('dni')} />
          </div>
          <Button type="button" variant="outline" onClick={handleBuscar} loading={isSearching}>
            Buscar
          </Button>
        </div>
        <Input label="Nombre" error={errors.nombre?.message} {...register('nombre')} />
        <Input label="Apellido" error={errors.apellido?.message} {...register('apellido')} />
        <Input label="Teléfono" error={errors.telefono?.message} {...register('telefono')} />
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
            Confirmar turno
          </Button>
        </div>
      </form>
    </Modal>
  )
}
