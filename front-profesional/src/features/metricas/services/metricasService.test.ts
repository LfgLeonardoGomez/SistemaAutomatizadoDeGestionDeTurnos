import { describe, expect, it, vi } from 'vitest'
import { api } from '../../../shared/services/api'
import { getMetricas } from './metricasService'
import type { Metricas } from '../../../shared/types'

describe('metricasService.getMetricas', () => {
  it('calls GET /profesional/metricas and returns the data', async () => {
    const data: Metricas = { turnos_hoy: 5, tasa_confirmacion_30d: 0.82, tasa_cancelacion_30d: 0.1 }
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await getMetricas()

    expect(getSpy).toHaveBeenCalledWith('/profesional/metricas')
    expect(result).toEqual(data)
  })
})
