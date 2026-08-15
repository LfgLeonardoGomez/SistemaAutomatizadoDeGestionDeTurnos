import { EstadoBadge } from '../../../shared/components/turno/EstadoBadge'
import { Button } from '../../../shared/components/ui/Button'
import type { TurnoConPaciente } from '../../../shared/types'

const BORDER_BY_ESTADO: Record<TurnoConPaciente['estado'], string> = {
  DISPONIBLE: 'border-l-estado-disponible',
  RESERVADO_TEMPORAL: 'border-l-estado-reservado',
  CONFIRMADO: 'border-l-estado-confirmado',
  CANCELADO: 'border-l-estado-cancelado',
  COMPLETADO: 'border-l-estado-completado',
}

interface TurnoRowProps {
  turno: TurnoConPaciente
  onCompletar: (turnoId: number) => void
  onCancelar: (turnoId: number) => void
}

export function TurnoRow({ turno, onCompletar, onCancelar }: TurnoRowProps) {
  return (
    <div
      className={`flex items-center justify-between rounded-lg border border-outline-variant border-l-4 bg-surface-container-lowest px-4 py-3 ${BORDER_BY_ESTADO[turno.estado]} ${
        turno.estado === 'CANCELADO' ? 'opacity-70' : ''
      }`}
    >
      <div className="flex items-center gap-4">
        <span className="w-28 text-body-md font-medium">
          {turno.hora_inicio}–{turno.hora_fin}
        </span>
        <span className={`text-body-md ${turno.estado === 'CANCELADO' ? 'line-through' : ''}`}>
          {turno.paciente ? `${turno.paciente.nombre} ${turno.paciente.apellido}` : 'Sin datos de paciente'}
        </span>
        <EstadoBadge estado={turno.estado} />
      </div>
      {turno.estado === 'CONFIRMADO' && (
        <div className="flex items-center gap-2">
          <Button type="button" onClick={() => onCompletar(turno.id)}>
            Completar
          </Button>
          <Button type="button" variant="danger" onClick={() => onCancelar(turno.id)}>
            Cancelar
          </Button>
        </div>
      )}
    </div>
  )
}
