import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DiasSelector } from './DiasSelector'

describe('DiasSelector', () => {
  it('marks the selected days as pressed', () => {
    render(<DiasSelector selected={['Lunes', 'Martes']} onChange={() => {}} />)
    expect(screen.getByRole('button', { name: 'Lunes' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Miércoles' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('adds a day when clicking an unselected one', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<DiasSelector selected={['Lunes']} onChange={onChange} />)

    await user.click(screen.getByRole('button', { name: 'Martes' }))
    expect(onChange).toHaveBeenCalledWith(['Lunes', 'Martes'])
  })

  it('removes a day when clicking an already-selected one', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<DiasSelector selected={['Lunes', 'Martes']} onChange={onChange} />)

    await user.click(screen.getByRole('button', { name: 'Lunes' }))
    expect(onChange).toHaveBeenCalledWith(['Martes'])
  })

  it('renders all 7 days of the week', () => {
    render(<DiasSelector selected={[]} onChange={() => {}} />)
    for (const dia of ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']) {
      expect(screen.getByRole('button', { name: dia })).toBeInTheDocument()
    }
  })
})
