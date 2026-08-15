import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SlotList } from './SlotList'
import type { SlotResponse } from '../../../shared/types'

const slots: SlotResponse[] = [
  { hora_inicio: '09:00', hora_fin: '09:30', disponible: true },
  { hora_inicio: '09:30', hora_fin: '10:00', disponible: false },
]

describe('SlotList', () => {
  it('shows an "Agendar" button only for available slots', async () => {
    const onAgendar = vi.fn()
    const user = userEvent.setup()
    render(<SlotList slots={slots} onAgendar={onAgendar} />)

    const buttons = screen.getAllByRole('button', { name: /agendar/i })
    expect(buttons).toHaveLength(1)

    await user.click(buttons[0])
    expect(onAgendar).toHaveBeenCalledWith('09:00')
  })

  it('shows both slot times', () => {
    render(<SlotList slots={slots} onAgendar={() => {}} />)
    expect(screen.getByText('09:00–09:30')).toBeInTheDocument()
    expect(screen.getByText('09:30–10:00')).toBeInTheDocument()
  })

  it('shows an empty state when there are no slots (day without atención)', () => {
    render(<SlotList slots={[]} onAgendar={() => {}} />)
    expect(screen.getByText(/no hay atención programada/i)).toBeInTheDocument()
  })
})
