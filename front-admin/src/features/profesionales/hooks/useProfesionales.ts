import { useQuery } from '@tanstack/react-query'
import { listProfesionales } from '../services/profesionalService'

export function useProfesionales() {
  return useQuery({
    queryKey: ['profesionales'],
    queryFn: () => listProfesionales({ skip: 0, limit: 100 }),
  })
}
