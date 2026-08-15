import { describe, expect, it } from 'vitest'
import { generateSlotGrid } from './slotGrid'

describe('generateSlotGrid', () => {
  it('generates 30-minute slots between horario_inicio and horario_fin', () => {
    const slots = generateSlotGrid('09:00', '11:00', 30)
    expect(slots).toEqual(['09:00', '09:30', '10:00', '10:30'])
  })

  it('does not include a slot that would start exactly at horario_fin', () => {
    const slots = generateSlotGrid('09:00', '10:00', 30)
    expect(slots).toEqual(['09:00', '09:30'])
  })

  it('handles a duracion that does not evenly divide the range', () => {
    const slots = generateSlotGrid('09:00', '10:00', 40)
    expect(slots).toEqual(['09:00', '09:40'])
  })

  it('returns an empty array when horario_inicio >= horario_fin', () => {
    expect(generateSlotGrid('10:00', '09:00', 30)).toEqual([])
    expect(generateSlotGrid('09:00', '09:00', 30)).toEqual([])
  })
})
