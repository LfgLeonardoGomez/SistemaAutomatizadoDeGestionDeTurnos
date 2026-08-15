import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { TelegramConfig } from '../components/TelegramConfig'
import { GoogleCalendarConfig } from '../components/GoogleCalendarConfig'
import { useIntegraciones } from '../hooks/useIntegraciones'

export default function IntegracionesPage() {
  const { data, isLoading } = useIntegraciones()
  const isHttps = window.location.protocol === 'https:'

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-headline-lg font-semibold">Integraciones</h1>
        <p className="text-body-md text-on-surface-variant">Conectá servicios externos a tu consultorio</p>
      </div>

      {!isHttps && (
        <p role="alert" className="rounded-lg bg-error-container px-3 py-2 text-label-md text-error">
          Necesitás HTTPS para actualizar las integraciones. Los cambios no se van a poder guardar en este entorno.
        </p>
      )}

      {isLoading || !data ? (
        <Skeleton count={2} className="h-40 w-full" />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <TelegramConfig hasTelegram={data.has_telegram} />
          <GoogleCalendarConfig hasGoogle={data.has_google} googleCalendarId={data.google_calendar_id} />
        </div>
      )}
    </div>
  )
}
