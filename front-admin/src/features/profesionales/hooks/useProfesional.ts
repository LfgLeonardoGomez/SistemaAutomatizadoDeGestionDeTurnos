import { useQuery } from '@tanstack/react-query'
import { getProfesional } from '../services/profesionalService'

export function useProfesional(id: number) {
  return useQuery({
    queryKey: ['profesionales', id],
    queryFn: () => getProfesional(id),
  })
}
