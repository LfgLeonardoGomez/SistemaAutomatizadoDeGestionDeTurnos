import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Modal } from './Modal'

describe('Modal', () => {
  it('renders nothing when closed', () => {
    render(
      <Modal isOpen={false} onClose={() => {}} title="Título">
        <p>Contenido</p>
      </Modal>,
    )
    expect(screen.queryByText('Contenido')).not.toBeInTheDocument()
  })

  it('renders the title and children when open', () => {
    render(
      <Modal isOpen onClose={() => {}} title="Nuevo profesional">
        <p>Contenido</p>
      </Modal>,
    )
    expect(screen.getByRole('heading', { name: 'Nuevo profesional' })).toBeInTheDocument()
    expect(screen.getByText('Contenido')).toBeInTheDocument()
  })

  it('calls onClose when clicking the close button', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(
      <Modal isOpen onClose={onClose} title="Nuevo profesional">
        <p>Contenido</p>
      </Modal>,
    )
    await user.click(screen.getByRole('button', { name: /cerrar/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when clicking the backdrop', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(
      <Modal isOpen onClose={onClose} title="Nuevo profesional">
        <p>Contenido</p>
      </Modal>,
    )
    await user.click(screen.getByTestId('modal-backdrop'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when pressing Escape', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(
      <Modal isOpen onClose={onClose} title="Nuevo profesional">
        <p>Contenido</p>
      </Modal>,
    )
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
