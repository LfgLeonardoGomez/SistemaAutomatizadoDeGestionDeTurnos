import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GlobalKpiCard } from './GlobalKpiCard'

describe('GlobalKpiCard', () => {
  it('formats an integer value with thousands separators', () => {
    render(<GlobalKpiCard label="Total turnos" value={3482} format="integer" />)
    expect(screen.getByText('3.482')).toBeInTheDocument()
    expect(screen.getByText('Total turnos')).toBeInTheDocument()
  })

  it('formats a percentage value from a 0-1 ratio', () => {
    render(<GlobalKpiCard label="Tasa confirmación 30d" value={0.815} format="percentage" />)
    expect(screen.getByText('81.5%')).toBeInTheDocument()
  })

  it('rounds percentage values to one decimal', () => {
    render(<GlobalKpiCard label="Tasa cancelación 30d" value={0.226} format="percentage" />)
    expect(screen.getByText('22.6%')).toBeInTheDocument()
  })

  it('applies an alert style when variant is "alert"', () => {
    render(<GlobalKpiCard label="Tasa cancelación 30d" value={0.226} format="percentage" variant="alert" />)
    expect(screen.getByText('ALERTA')).toBeInTheDocument()
  })

  it('does not show the ALERTA label for the default variant', () => {
    render(<GlobalKpiCard label="Total turnos" value={3482} format="integer" />)
    expect(screen.queryByText('ALERTA')).not.toBeInTheDocument()
  })
})
