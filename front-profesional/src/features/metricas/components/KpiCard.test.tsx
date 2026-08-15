import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { KpiCard } from './KpiCard'

describe('KpiCard', () => {
  it('formats an integer value', () => {
    render(<KpiCard label="Turnos hoy" value={5} format="integer" />)
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('Turnos hoy')).toBeInTheDocument()
  })

  it('formats a percentage value from a 0-1 ratio', () => {
    render(<KpiCard label="Tasa confirmación 30d" value={0.82} format="percentage" />)
    expect(screen.getByText('82.0%')).toBeInTheDocument()
  })

  it('applies an alert style when variant is "alert"', () => {
    render(<KpiCard label="Tasa cancelación 30d" value={0.25} format="percentage" variant="alert" />)
    expect(screen.getByText('ALERTA')).toBeInTheDocument()
  })

  it('does not show ALERTA for the default variant', () => {
    render(<KpiCard label="Turnos hoy" value={5} format="integer" />)
    expect(screen.queryByText('ALERTA')).not.toBeInTheDocument()
  })
})
