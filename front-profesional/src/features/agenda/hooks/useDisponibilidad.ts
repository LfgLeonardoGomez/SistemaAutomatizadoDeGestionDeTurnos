import { useQuery } from '@tanstack/react-query'
import { getDisponibilidad } from '../services/turnoService'
import { getConfiguracion } from '../../configuracion/services/configuracionService'
import { generateSlotGrid } from '../utils/slotGrid'
import type { SlotResponse } from '../../../shared/types'

function computeMinutesGrid(horarioInicio: string, horarioFin: string, duracionTurno: number, disponibles: SlotResponse[]) {
  const disponiblesByHora = new Map(disponibles.map((s) => [s.hora_inicio, s]))
  return generateSlotGrid(horarioInicio, horarioFin, duracionTurno).map((horaInicio) => {
    const slot = disponiblesByHora.get(horaInicio)
    if (slot) return slot
    const [h, m] = horaInicio.split(':').map(Number)
    const finMin = h * 60 + m + duracionTurno
    const horaFin = `${String(Math.floor(finMin / 60)).padStart(2, '0')}:${String(finMin % 60).padStart(2, '0')}`
    return { hora_inicio: horaInicio, hora_fin: horaFin, disponible: false }
  })
}

export function useDisponibilidad(fecha: string) {
  const configQuery = useQuery({
    queryKey: ['profesional-configuracion'],
    queryFn: getConfiguracion,
  })
  const disponibilidadQuery = useQuery({
    queryKey: ['disponibilidad', fecha],
    queryFn: () => getDisponibilidad(fecha),
    enabled: Boolean(configQuery.data),
  })

  const isLoading = configQuery.isLoading || disponibilidadQuery.isLoading
  const slots =
    configQuery.data && disponibilidadQuery.data
      ? computeMinutesGrid(
          configQuery.data.horario_inicio,
          configQuery.data.horario_fin,
          configQuery.data.duracion_turno,
          disponibilidadQuery.data,
        )
      : []

  return {
    slots,
    isLoading,
    isError: configQuery.isError || disponibilidadQuery.isError,
    disponiblesCount: slots.filter((s) => s.disponible).length,
    ocupadosCount: slots.filter((s) => !s.disponible).length,
  }
}
