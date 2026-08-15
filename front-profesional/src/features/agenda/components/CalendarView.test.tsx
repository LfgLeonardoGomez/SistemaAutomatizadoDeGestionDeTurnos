import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CalendarView } from './CalendarView'

describe('CalendarView', () => {
  it('shows the month and year for the selected date', () => {
    render(<CalendarView selectedDate={new Date(2026, 7, 15)} onSelectDate={() => {}} />)
    expect(screen.getByText(/agosto 2026/i)).toBeInTheDocument()
  })

  it('calls onSelectDate when clicking a day in the current month', async () => {
    const onSelectDate = vi.fn()
    const user = userEvent.setup()
    render(<CalendarView selectedDate={new Date(2026, 7, 15)} onSelectDate={onSelectDate} />)

    await user.click(screen.getByRole('button', { name: '20' }))

    const calledWith = onSelectDate.mock.calls[0][0] as Date
    expect(calledWith.getDate()).toBe(20)
    expect(calledWith.getMonth()).toBe(7)
  })

  it('navigates to the next month and shows its days', async () => {
    const user = userEvent.setup()
    render(<CalendarView selectedDate={new Date(2026, 7, 15)} onSelectDate={() => {}} />)

    await user.click(screen.getByRole('button', { name: /mes siguiente/i }))
    expect(await screen.findByText(/septiembre 2026/i)).toBeInTheDocument()
  })

  it('navigates to the previous month', async () => {
    const user = userEvent.setup()
    render(<CalendarView selectedDate={new Date(2026, 7, 15)} onSelectDate={() => {}} />)

    await user.click(screen.getByRole('button', { name: /mes anterior/i }))
    expect(await screen.findByText(/julio 2026/i)).toBeInTheDocument()
  })
})
