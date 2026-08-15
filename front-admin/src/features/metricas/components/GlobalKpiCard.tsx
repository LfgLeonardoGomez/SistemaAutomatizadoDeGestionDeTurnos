const integerFormatter = new Intl.NumberFormat('es-AR')

interface GlobalKpiCardProps {
  label: string
  value: number
  format: 'integer' | 'percentage'
  variant?: 'default' | 'highlight' | 'alert'
}

function formatValue(value: number, format: 'integer' | 'percentage'): string {
  if (format === 'percentage') {
    return `${(value * 100).toFixed(1)}%`
  }
  return integerFormatter.format(value)
}

export function GlobalKpiCard({ label, value, format, variant = 'default' }: GlobalKpiCardProps) {
  const variantClasses =
    variant === 'highlight'
      ? 'border-b-2 border-primary bg-primary-container/10'
      : variant === 'alert'
        ? 'border border-error bg-error-container/40'
        : 'border border-outline-variant bg-surface-container-lowest'

  return (
    <div className={`rounded-lg p-4 shadow-sm ${variantClasses}`}>
      <div className="flex items-center justify-between">
        <span className="text-label-md text-on-surface-variant">{label}</span>
        {variant === 'alert' && (
          <span className="text-label-sm font-semibold text-error">ALERTA</span>
        )}
      </div>
      <p className="text-headline-lg font-semibold">{formatValue(value, format)}</p>
    </div>
  )
}
