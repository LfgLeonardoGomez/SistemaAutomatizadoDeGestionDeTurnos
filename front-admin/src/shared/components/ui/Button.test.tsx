import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Button } from './Button'

describe('Button', () => {
  it('merges a custom className with the variant classes instead of overriding them', () => {
    render(<Button className="mt-6 w-full">Click</Button>)
    const button = screen.getByRole('button', { name: 'Click' })
    expect(button.className).toContain('mt-6')
    expect(button.className).toContain('w-full')
    expect(button.className).toContain('bg-primary')
  })
})
