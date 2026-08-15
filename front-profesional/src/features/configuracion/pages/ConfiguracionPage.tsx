import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { Input } from '../../../shared/components/ui/Input'
import { Button } from '../../../shared/components/ui/Button'
import { DiasSelector } from '../components/DiasSelector'
import { useConfiguracion, useUpdateConfiguracion } from '../hooks/useConfiguracion'

const configSchema = z
  .object({
    horario_inicio: z.string().min(1, 'La hora de inicio es requerida'),
    horario_fin: z.string().min(1, 'La hora de fin es requerida'),
    duracion_turno: z.coerce.number().int().positive('La duración debe ser mayor a 0'),
    dias_atencion: z.array(z.string()).min(1, 'Seleccioná al menos un día'),
  })
  .refine((data) => data.horario_inicio < data.horario_fin, {
    message: 'La hora de inicio debe ser menor a la hora de fin',
    path: ['horario_fin'],
  })

type ConfigFormValues = z.infer<typeof configSchema>

export default function ConfiguracionPage() {
  const { data, isLoading } = useConfiguracion()
  const { mutate, isPending, isSuccess } = useUpdateConfiguracion()
  const [showSuccess, setShowSuccess] = useState(false)
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<ConfigFormValues>({ resolver: zodResolver(configSchema) })

  useEffect(() => {
    if (data) {
      reset({
        horario_inicio: data.horario_inicio,
        horario_fin: data.horario_fin,
        duracion_turno: data.duracion_turno,
        dias_atencion: data.dias_atencion,
      })
    }
  }, [data, reset])

  useEffect(() => {
    if (isSuccess) {
      setShowSuccess(true)
      const timeout = setTimeout(() => setShowSuccess(false), 3000)
      return () => clearTimeout(timeout)
    }
  }, [isSuccess])

  if (isLoading || !data) {
    return <Skeleton count={4} />
  }

  const diasAtencion = watch('dias_atencion') ?? []

  function onSubmit(values: ConfigFormValues) {
    mutate(values)
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-headline-lg font-semibold">Configuración</h1>
        <p className="text-body-md text-on-surface-variant">Definí los parámetros de atención de tu consultorio</p>
      </div>

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="flex max-w-lg flex-col gap-4 rounded-xl border border-outline-variant bg-surface-container-lowest p-6"
        noValidate
      >
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Hora de inicio"
            type="time"
            error={errors.horario_inicio?.message}
            {...register('horario_inicio')}
          />
          <Input
            label="Hora de fin"
            type="time"
            error={errors.horario_fin?.message}
            {...register('horario_fin')}
          />
        </div>

        <div>
          <span className="mb-1 block text-label-md font-medium text-on-surface-variant">Días de atención</span>
          <DiasSelector selected={diasAtencion} onChange={(dias) => setValue('dias_atencion', dias)} />
          {errors.dias_atencion && (
            <span role="alert" className="mt-1 block text-label-sm text-error">
              {errors.dias_atencion.message}
            </span>
          )}
        </div>

        <Input
          label="Duración del turno (minutos)"
          type="number"
          error={errors.duracion_turno?.message}
          {...register('duracion_turno')}
        />

        <Input label="Especialidad" value={data.especialidad} readOnly />

        {showSuccess && (
          <p className="rounded-lg bg-estado-completado/10 px-3 py-2 text-label-md text-estado-completado">
            Cambios guardados
          </p>
        )}

        <Button type="submit" loading={isPending} className="self-start">
          Guardar cambios
        </Button>
      </form>
    </div>
  )
}
