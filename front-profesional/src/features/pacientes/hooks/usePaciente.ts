import { useQuery } from '@tanstack/react-query'
import { getPaciente } from '../services/pacienteService'

export function usePaciente(id: number) {
  return useQuery({
    queryKey: ['pacientes', id],
    queryFn: () => getPaciente(id),
  })
}
