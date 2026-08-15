import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { GlobalKpiCard } from '../components/GlobalKpiCard'
import { useGlobalMetricas } from '../hooks/useGlobalMetricas'

const CANCELACION_ALERT_THRESHOLD = 0.2

export default function MetricasPage() {
  const { data, isLoading } = useGlobalMetricas()

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-headline-sm font-semibold">Métricas globales</h1>
        <p className="text-body-md text-on-surface-variant">
          Estado operativo de la red de profesionales
        </p>
      </div>

      {isLoading || !data ? (
        <Skeleton count={6} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <GlobalKpiCard label="Total profesionales" value={data.total_profesionales} format="integer" />
          <GlobalKpiCard
            label="Profesionales activos"
            value={data.profesionales_activos}
            format="integer"
          />
          <GlobalKpiCard
            label="Profesionales inactivos"
            value={data.profesionales_inactivos}
            format="integer"
          />
          <GlobalKpiCard label="Total turnos" value={data.total_turnos} format="integer" />
          <GlobalKpiCard
            label="Turnos hoy"
            value={data.turnos_hoy}
            format="integer"
            variant="highlight"
          />
          <GlobalKpiCard
            label="Turnos confirmados 30d"
            value={data.turnos_confirmados_30d}
            format="integer"
          />
          <GlobalKpiCard
            label="Turnos cancelados 30d"
            value={data.turnos_cancelados_30d}
            format="integer"
          />
          <GlobalKpiCard label="Total pacientes" value={data.total_pacientes} format="integer" />
          <GlobalKpiCard
            label="Tasa confirmación 30d"
            value={data.tasa_confirmacion_30d}
            format="percentage"
          />
          <GlobalKpiCard
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
