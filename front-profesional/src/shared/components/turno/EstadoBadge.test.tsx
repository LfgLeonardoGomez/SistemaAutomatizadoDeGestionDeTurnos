import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EstadoBadge } from './EstadoBadge'

describe('EstadoBadge', () => {
  it.each([
    ['DISPONIBLE', 'Disponible'],
    ['RESERVADO_TEMPORAL', 'Reservado'],
    ['CONFIRMADO', 'Confirmado'],
    ['CANCELADO', 'Cancelado'],
    ['COMPLETADO', 'Completado'],
  ] as const)('renders the label for %s', (estado, label) => {
    render(<EstadoBadge estado={estado} />)
    expect(screen.getByText(label)).toBeInTheDocument()
  })
})
