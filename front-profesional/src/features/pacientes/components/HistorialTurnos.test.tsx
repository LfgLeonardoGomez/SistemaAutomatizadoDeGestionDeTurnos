import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HistorialTurnos } from './HistorialTurnos'
import type { Turno } from '../../../shared/types'

const turnos: Turno[] = [
  {
    id: 1,
    fecha: '2026-08-10',
    hora_inicio: '09:00',
    hora_fin: '09:30',
    estado: 'COMPLETADO',
    profesional_id: 1,
    paciente_id: 5,
    google_event_id: null,
    creado_en: '2026-08-01T00:00:00Z',
  },
]

describe('HistorialTurnos', () => {
  it('renders a row per turno with fecha, hora and estado', () => {
    render(<HistorialTurnos turnos={turnos} />)
    expect(screen.getByText('10/08/2026')).toBeInTheDocument()
    expect(screen.getByText('09:00–09:30')).toBeInTheDocument()
    expect(screen.getByText('Completado')).toBeInTheDocument()
  })

  it('shows an empty state when there are no turnos', () => {
    render(<HistorialTurnos turnos={[]} />)
    expect(screen.getByText(/sin turnos registrados/i)).toBeInTheDocument()
  })
})
