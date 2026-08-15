import { EmptyState } from '../../../shared/components/ui/EmptyState'
import type { SlotResponse } from '../../../shared/types'

interface SlotListProps {
  slots: SlotResponse[]
  onAgendar: (horaInicio: string) => void
}

export function SlotList({ slots, onAgendar }: SlotListProps) {
  if (slots.length === 0) {
    return (
      <EmptyState
        title="No hay atención programada"
        description="Este día no está dentro de tus días u horario de atención."
      />
    )
  }

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {slots.map((slot) => (
        <div
          key={slot.hora_inicio}
          className={`flex flex-col items-center gap-1 rounded-lg border p-3 ${
            slot.disponible
              ? 'border-dashed border-outline-variant hover:border-primary'
              : 'border-outline-variant bg-surface-container-low'
          }`}
        >
          <span className="text-body-md font-medium">
            {slot.hora_inicio}–{slot.hora_fin}
          </span>
          {slot.disponible ? (
            <button
              type="button"
              onClick={() => onAgendar(slot.hora_inicio)}
              className="text-label-sm font-semibold text-primary hover:underline"
            >
              + Agendar
            </button>
          ) : (
            <span className="text-label-sm text-on-surface-variant">Ocupado</span>
          )}
        </div>
      ))}
    </div>
  )
}
