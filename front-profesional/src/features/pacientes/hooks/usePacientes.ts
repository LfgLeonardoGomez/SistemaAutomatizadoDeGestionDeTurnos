import { useQuery } from '@tanstack/react-query'
import { listPacientes } from '../services/pacienteService'

export function usePacientes() {
  return useQuery({
    queryKey: ['pacientes'],
    queryFn: () => listPacientes({ limit: 100, offset: 0 }),
  })
}
