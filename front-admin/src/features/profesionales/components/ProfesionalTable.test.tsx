import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProfesionalTable } from './ProfesionalTable'
import type { ProfesionalAdminResponse } from '../../../shared/types'

const profesionales: ProfesionalAdminResponse[] = [
  {
    id: 9021,
    nombre: 'Dr. Ricardo Mendoza',
    especialidad: 'Odontología general',
    email: 'ricardo@clinica.com',
    is_active: true,
    creado_en: '2026-01-15T00:00:00Z',
  },
  {
    id: 9015,
    nombre: 'Dr. Alberto Garcia',
    especialidad: 'Ortodoncia',
    email: 'alberto@clinica.com',
    is_active: false,
    creado_en: '2026-02-20T00:00:00Z',
  },
]

function renderTable(props: Partial<React.ComponentProps<typeof ProfesionalTable>> = {}) {
  return render(
    <MemoryRouter>
      <ProfesionalTable profesionales={profesionales} onToggleActive={() => {}} {...props} />
    </MemoryRouter>,
  )
}

describe('ProfesionalTable', () => {
  it('renders one row per profesional with name, email, especialidad', () => {
    renderTable()
    expect(screen.getByText('Dr. Ricardo Mendoza')).toBeInTheDocument()
    expect(screen.getByText('ricardo@clinica.com')).toBeInTheDocument()
    expect(screen.getByText('Odontología general')).toBeInTheDocument()
    expect(screen.getByText('Dr. Alberto Garcia')).toBeInTheDocument()
  })

  it('shows an "Activo" badge for active profesionales and "Inactivo" for inactive ones', () => {
    renderTable()
    expect(screen.getByText('Activo')).toBeInTheDocument()
    expect(screen.getByText('Inactivo')).toBeInTheDocument()
  })

  it('shows a "Desactivar" action for active profesionales and "Activar" for inactive ones', () => {
    renderTable()
    expect(screen.getByRole('button', { name: /desactivar/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^activar$/i })).toBeInTheDocument()
  })

  it('links each row to its detail page', () => {
    renderTable()
    expect(screen.getByRole('link', { name: /dr\. ricardo mendoza/i })).toHaveAttribute(
      'href',
      '/profesionales/9021',
    )
  })
})
