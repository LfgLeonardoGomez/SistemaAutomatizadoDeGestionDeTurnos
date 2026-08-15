import { describe, expect, it, vi } from 'vitest'
import { api } from '../../../shared/services/api'
import { getConfiguracion, updateConfiguracion } from './configuracionService'
import type { ProfesionalConfig } from '../../../shared/types'

describe('configuracionService.getConfiguracion', () => {
  it('calls GET /profesional/configuracion and returns the data', async () => {
    const data: ProfesionalConfig = {
      horario_inicio: '09:00',
      horario_fin: '17:00',
      dias_atencion: ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'],
      duracion_turno: 30,
      especialidad: 'Odontología general',
    }
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await getConfiguracion()

    expect(getSpy).toHaveBeenCalledWith('/profesional/configuracion')
    expect(result).toEqual(data)
  })
})

describe('configuracionService.updateConfiguracion', () => {
  it('calls PUT /profesional/configuracion with the update and returns the updated config', async () => {
    const updated: ProfesionalConfig = {
      horario_inicio: '10:00',
      horario_fin: '18:00',
      dias_atencion: ['Lunes', 'Martes'],
      duracion_turno: 45,
      especialidad: 'Odontología general',
    }
    const putSpy = vi.spyOn(api, 'put').mockResolvedValue({ data: updated })

    const payload = { horario_inicio: '10:00', horario_fin: '18:00', dias_atencion: ['Lunes', 'Martes'], duracion_turno: 45 }
    const result = await updateConfiguracion(payload)

    expect(putSpy).toHaveBeenCalledWith('/profesional/configuracion', payload)
    expect(result).toEqual(updated)
  })
})
