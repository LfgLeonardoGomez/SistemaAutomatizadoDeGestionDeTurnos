import { describe, expect, it, vi } from 'vitest'
import { api } from '../../../shared/services/api'
import { getIntegraciones, updateIntegraciones } from './integracionesService'
import type { Integraciones } from '../../../shared/types'

describe('integracionesService.getIntegraciones', () => {
  it('calls GET /profesional/integraciones and returns the data', async () => {
    const data: Integraciones = { has_telegram: true, has_google: false, google_calendar_id: 'primary' }
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await getIntegraciones()

    expect(getSpy).toHaveBeenCalledWith('/profesional/integraciones')
    expect(result).toEqual(data)
  })
})

describe('integracionesService.updateIntegraciones', () => {
  it('calls PUT /profesional/integraciones with the update and returns the updated data', async () => {
    const data: Integraciones = { has_telegram: true, has_google: false, google_calendar_id: 'primary' }
    const putSpy = vi.spyOn(api, 'put').mockResolvedValue({ data })

    const payload = { telegram_bot_token: 'abc123' }
    const result = await updateIntegraciones(payload)

    expect(putSpy).toHaveBeenCalledWith('/profesional/integraciones', payload)
    expect(result).toEqual(data)
  })
})
