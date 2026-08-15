import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { KpiCard } from '../components/KpiCard'
import { useMetricas } from '../hooks/useMetricas'

const CANCELACION_ALERT_THRESHOLD = 0.2

export default function MetricasPage() {
  const { data, isLoading } = useMetricas()

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-headline-lg font-semibold">Métricas</h1>
        <p className="text-body-md text-on-surface-variant">Indicadores de tu consultorio, últimos 30 días</p>
      </div>

      {isLoading || !data ? (
        <Skeleton count={3} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <KpiCard label="Turnos hoy" value={data.turnos_hoy} format="integer" />
          <KpiCard label="Tasa confirmación 30d" value={data.tasa_confirmacion_30d} format="percentage" />
          <KpiCard
            label="Tasa cancelación 30d"
            value={data.tasa_cancelacion_30d}
            format="percentage"
            variant={data.tasa_cancelacion_30d > CANCELACION_ALERT_THRESHOLD ? 'alert' : 'default'}
          />
        </div>
      )}
    </div>
  )
}
