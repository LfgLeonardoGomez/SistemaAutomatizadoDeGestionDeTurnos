import type { ReactNode } from 'react'

interface BadgeProps {
  variant: 'success' | 'neutral' | 'danger'
  children: ReactNode
}

const VARIANT_CLASSES: Record<BadgeProps['variant'], string> = {
  success: 'bg-estado-completado/10 text-estado-completado',
  neutral: 'bg-outline-variant/40 text-on-surface-variant',
  danger: 'bg-estado-cancelado/10 text-estado-cancelado',
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
