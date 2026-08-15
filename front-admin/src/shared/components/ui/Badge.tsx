import type { ReactNode } from 'react'

interface BadgeProps {
  variant: 'success' | 'neutral' | 'danger'
  children: ReactNode
}

const VARIANT_CLASSES: Record<BadgeProps['variant'], string> = {
  success: 'bg-success/10 text-success',
  neutral: 'bg-outline-variant/40 text-on-surface-variant',
  danger: 'bg-danger/10 text-danger',
}

export function Badge({ variant, children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-label-sm font-semibold ${VARIANT_CLASSES[variant]}`}
    >
      {children}
    </span>
  )
}
