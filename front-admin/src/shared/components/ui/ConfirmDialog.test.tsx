import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConfirmDialog } from './ConfirmDialog'

describe('ConfirmDialog', () => {
  it('renders nothing when closed', () => {
    render(<ConfirmDialog isOpen={false} message="¿Estás seguro?" onConfirm={() => {}} onCancel={() => {}} />)
    expect(screen.queryByText('¿Estás seguro?')).not.toBeInTheDocument()
  })

  it('shows the message when open', () => {
    render(<ConfirmDialog isOpen message="¿Desactivar a Dr. Mendoza?" onConfirm={() => {}} onCancel={() => {}} />)
    expect(screen.getByText('¿Desactivar a Dr. Mendoza?')).toBeInTheDocument()
  })

  it('calls onConfirm when clicking the confirm button', async () => {
    const onConfirm = vi.fn()
    const user = userEvent.setup()
    render(<ConfirmDialog isOpen message="¿Seguro?" onConfirm={onConfirm} onCancel={() => {}} />)
    await user.click(screen.getByRole('button', { name: /confirmar/i }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('calls onCancel when clicking the cancel button', async () => {
    const onCancel = vi.fn()
    const user = userEvent.setup()
    render(<ConfirmDialog isOpen message="¿Seguro?" onConfirm={() => {}} onCancel={onCancel} />)
    await user.click(screen.getByRole('button', { name: /cancelar/i }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('uses a custom confirmLabel when provided', () => {
    render(
      <ConfirmDialog
        isOpen
        message="¿Seguro?"
        confirmLabel="Desactivar"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    )
    expect(screen.getByRole('button', { name: 'Desactivar' })).toBeInTheDocument()
  })
})
