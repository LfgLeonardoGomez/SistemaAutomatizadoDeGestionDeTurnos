import { useState } from 'react'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { EmptyState } from '../../../shared/components/ui/EmptyState'
import { ConfirmDialog } from '../../../shared/components/ui/ConfirmDialog'
import { TurnoRow } from '../components/TurnoRow'
import { useCancelarTurno, useCompletarTurno, useTurnosHoy } from '../hooks/useTurnosHoy'

export default function DashboardPage() {
  const { data, isLoading } = useTurnosHoy()
  const completar = useCompletarTurno()
  const cancelar = useCancelarTurno()
  const [pendingCancelId, setPendingCancelId] = useState<number | null>(null)

  const turnos = data ?? []

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <div>
          <h1 className="text-headline-lg font-semibold">Turnos de hoy</h1>
          <p className="text-body-md text-on-surface-variant">
            {new Date().toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })}
          </p>
        </div>
        {!isLoading && (
          <span className="rounded-full bg-primary-container/10 px-3 py-1 text-label-sm font-semibold text-primary">
            {turnos.length} turnos
          </span>
        )}
      </div>

      {isLoading ? (
        <Skeleton count={4} />
      ) : turnos.length === 0 ? (
        <EmptyState
          title="No tenés turnos programados para hoy"
          description="Cuando tengas turnos confirmados para hoy, van a aparecer acá."
        />
      ) : (
        <div className="flex flex-col gap-3">
          {turnos.map((turno) => (
            <TurnoRow
              key={turno.id}
              turno={turno}
              onCompletar={(id) => completar.mutate(id)}
              onCancelar={(id) => setPendingCancelId(id)}
            />
          ))}
        </div>
      )}

      <ConfirmDialog
        isOpen={pendingCancelId !== null}
        message="¿Estás seguro de cancelar este turno?"
        confirmLabel="Cancelar turno"
        isLoading={cancelar.isPending}
        onCancel={() => setPendingCancelId(null)}
        onConfirm={() => {
          if (pendingCancelId === null) return
          cancelar.mutate(pendingCancelId, { onSuccess: () => setPendingCancelId(null) })
        }}
      />
    </div>
  )
}
