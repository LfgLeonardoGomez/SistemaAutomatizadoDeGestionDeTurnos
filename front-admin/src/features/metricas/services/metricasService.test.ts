import { describe, expect, it, vi } from 'vitest'
import { api } from '../../../shared/services/api'
import { getGlobalMetrics } from './metricasService'
import type { GlobalMetrics } from '../../../shared/types'

describe('metricasService.getGlobalMetrics', () => {
  it('calls GET /admin/metricas and returns the data', async () => {
    const data: GlobalMetrics = {
      total_profesionales: 142,
      profesionales_activos: 128,
      profesionales_inactivos: 14,
      total_turnos: 3482,
      turnos_hoy: 214,
      turnos_confirmados_30d: 2840,
      turnos_cancelados_30d: 642,
      total_pacientes: 8912,
      tasa_confirmacion_30d: 0.815,
      tasa_cancelacion_30d: 0.226,
    }
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await getGlobalMetrics()

    expect(getSpy).toHaveBeenCalledWith('/admin/metricas')
    expect(result).toEqual(data)
  })
})
