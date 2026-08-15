import type { TurnoEstado } from '../../types'

const ESTADO_CONFIG: Record<TurnoEstado, { label: string; className: string }> = {
  DISPONIBLE: { label: 'Disponible', className: 'bg-estado-disponible/10 text-estado-disponible' },
  RESERVADO_TEMPORAL: { label: 'Reservado', className: 'bg-estado-reservado/10 text-estado-reservado' },
  CONFIRMADO: { label: 'Confirmado', className: 'bg-estado-confirmado/10 text-estado-confirmado' },
  CANCELADO: { label: 'Cancelado', className: 'bg-estado-cancelado/10 text-estado-cancelado' },
  COMPLETADO: { label: 'Completado', className: 'bg-estado-completado/10 text-estado-completado' },
}

export function EstadoBadge({ estado }: { estado: TurnoEstado }) {
  const config = ESTADO_CONFIG[estado]
  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-label-sm font-semibold ${config.className}`}>
      {config.label}
    </span>
  )
}
