import { describe, expect, it, vi } from 'vitest'
import { api } from '../../../shared/services/api'
import {
  activateProfesional,
  createProfesional,
  deactivateProfesional,
  getProfesional,
  listProfesionales,
} from './profesionalService'
import type {
  ProfesionalAdminResponse,
  ProfesionalCreateResponse,
} from '../../../shared/types'

describe('profesionalService.listProfesionales', () => {
  it('calls GET /admin/profesionales with skip/limit and returns the data', async () => {
    const data: ProfesionalAdminResponse[] = [
      {
        id: 1,
        nombre: 'Dr. Ricardo Mendoza',
        especialidad: 'Odontología general',
        email: 'ricardo@clinica.com',
        is_active: true,
        creado_en: '2026-01-01T00:00:00Z',
      },
    ]
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await listProfesionales({ skip: 0, limit: 100 })

    expect(getSpy).toHaveBeenCalledWith('/admin/profesionales', { params: { skip: 0, limit: 100 } })
    expect(result).toEqual(data)
  })
})

describe('profesionalService.createProfesional', () => {
  it('calls POST /admin/profesionales and returns the created profesional with credentials', async () => {
    const response: ProfesionalCreateResponse = {
      id: 5,
      nombre: 'Dr. Alejandro Méndez',
      email: 'alejandro@clinica.com',
      especialidad: 'Ortodoncia',
      is_active: true,
      duracion_turno: 30,
      horario_inicio: '09:00',
      horario_fin: '18:00',
      dias_atencion: ['lunes', 'martes'],
      api_key: 'pk_live_abc123',
      telegram_secret_token: 'tg_secret_xyz',
    }
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: response })

    const payload = {
      nombre: 'Dr. Alejandro Méndez',
      email: 'alejandro@clinica.com',
      especialidad: 'Ortodoncia',
      password: 'password123',
    }
    const result = await createProfesional(payload)

    expect(postSpy).toHaveBeenCalledWith('/admin/profesionales', payload)
    expect(result).toEqual(response)
  })
})

describe('profesionalService.getProfesional', () => {
  it('calls GET /admin/profesionales/{id} and returns the profesional', async () => {
    const profesional: ProfesionalAdminResponse = {
      id: 9021,
      nombre: 'Dr. Ricardo Mendoza',
      especialidad: 'Odontología general',
      email: 'ricardo@clinica.com',
      is_active: true,
      creado_en: '2026-01-01T00:00:00Z',
    }
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: profesional })

    const result = await getProfesional(9021)

    expect(getSpy).toHaveBeenCalledWith('/admin/profesionales/9021')
    expect(result).toEqual(profesional)
  })
})

describe('profesionalService.activateProfesional / deactivateProfesional', () => {
  const profesional: ProfesionalAdminResponse = {
    id: 9021,
    nombre: 'Dr. Ricardo Mendoza',
    especialidad: 'Odontología general',
    email: 'ricardo@clinica.com',
    is_active: true,
    creado_en: '2026-01-01T00:00:00Z',
  }

  it('calls PUT /admin/profesionales/{id}/activar and returns the updated profesional', async () => {
    const putSpy = vi.spyOn(api, 'put').mockResolvedValue({ data: profesional })

    const result = await activateProfesional(9021)

    expect(putSpy).toHaveBeenCalledWith('/admin/profesionales/9021/activar')
    expect(result).toEqual(profesional)
  })

  it('calls PUT /admin/profesionales/{id}/desactivar and returns the updated profesional', async () => {
    const inactive = { ...profesional, is_active: false }
    const putSpy = vi.spyOn(api, 'put').mockResolvedValue({ data: inactive })

    const result = await deactivateProfesional(9021)

    expect(putSpy).toHaveBeenCalledWith('/admin/profesionales/9021/desactivar')
    expect(result).toEqual(inactive)
  })
})
