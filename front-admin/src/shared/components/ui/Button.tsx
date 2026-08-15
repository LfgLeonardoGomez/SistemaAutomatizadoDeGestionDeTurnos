import type { ButtonHTMLAttributes } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'outline'
  loading?: boolean
}

export function Button({ variant = 'primary', loading, disabled, children, className, ...props }: ButtonProps) {
  const base = 'rounded-lg px-4 py-2 text-body-md font-semibold transition-colors disabled:opacity-60'
  const variants = {
    primary: 'bg-primary text-on-primary hover:bg-primary-container',
    outline: 'border border-primary text-primary hover:bg-primary-container/10',
  }

  return (
    <button
      className={`${base} ${variants[variant]} ${className ?? ''}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? 'Cargando...' : children}
    </button>
  )
}
