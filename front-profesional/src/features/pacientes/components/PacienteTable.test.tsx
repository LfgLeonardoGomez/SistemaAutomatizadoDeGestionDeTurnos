import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { PacienteTable } from './PacienteTable'
import type { Paciente } from '../../../shared/types'

const pacientes: Paciente[] = [
  { id: 5, nombre: 'Juan', apellido: 'Pérez', dni: '12345678', telefono: '555-0001', creado_en: '2026-01-15T00:00:00Z' },
]

describe('PacienteTable', () => {
  it('renders paciente rows with name, dni, telefono', () => {
    render(
      <MemoryRouter>
        <PacienteTable pacientes={pacientes} />
      </MemoryRouter>,
    )
    expect(screen.getByText('Juan Pérez')).toBeInTheDocument()
    expect(screen.getByText('12345678')).toBeInTheDocument()
    expect(screen.getByText('555-0001')).toBeInTheDocument()
  })

  it('links each row to its detail page', () => {
    render(
      <MemoryRouter>
        <PacienteTable pacientes={pacientes} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: /juan pérez/i })).toHaveAttribute('href', '/pacientes/5')
  })
})
