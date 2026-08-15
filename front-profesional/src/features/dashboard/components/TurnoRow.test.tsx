import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TurnoRow } from './TurnoRow'
import type { TurnoConPaciente } from '../../../shared/types'

const confirmado: TurnoConPaciente = {
  id: 1,
  fecha: '2026-08-15',
  hora_inicio: '09:00',
  hora_fin: '09:30',
  estado: 'CONFIRMADO',
  profesional_id: 1,
  paciente_id: 5,
  paciente: { id: 5, nombre: 'Juan', apellido: 'Pérez', dni: '12345678', telefono: '555-0001' },
}

describe('TurnoRow', () => {
  it('shows the hora, paciente name, and estado badge', () => {
    render(<TurnoRow turno={confirmado} onCompletar={() => {}} onCancelar={() => {}} />)
    expect(screen.getByText('09:00–09:30')).toBeInTheDocument()
    expect(screen.getByText('Juan Pérez')).toBeInTheDocument()
    expect(screen.getByText('Confirmado')).toBeInTheDocument()
  })

  it('shows Completar and Cancelar actions for a CONFIRMADO turno', async () => {
    const onCompletar = vi.fn()
    const onCancelar = vi.fn()
    const user = userEvent.setup()
    render(<TurnoRow turno={confirmado} onCompletar={onCompletar} onCancelar={onCancelar} />)

    await user.click(screen.getByRole('button', { name: /completar/i }))
    expect(onCompletar).toHaveBeenCalledWith(1)

    await user.click(screen.getByRole('button', { name: /^cancelar$/i }))
    expect(onCancelar).toHaveBeenCalledWith(1)
  })

  it('shows no actions for a non-CONFIRMADO turno', () => {
    render(
      <TurnoRow
        turno={{ ...confirmado, estado: 'COMPLETADO' }}
        onCompletar={() => {}}
        onCancelar={() => {}}
      />,
    )
    expect(screen.queryByRole('button', { name: /completar/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^cancelar$/i })).not.toBeInTheDocument()
  })

  it('shows "Paciente" as fallback when there is no paciente data', () => {
    render(
      <TurnoRow turno={{ ...confirmado, paciente: null }} onCompletar={() => {}} onCancelar={() => {}} />,
    )
    expect(screen.getByText(/sin datos de paciente/i)).toBeInTheDocument()
  })
})
