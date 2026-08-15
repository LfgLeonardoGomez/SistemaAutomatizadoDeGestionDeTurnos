import { useState } from 'react'
import { Badge } from '../../../shared/components/ui/Badge'
import { Input } from '../../../shared/components/ui/Input'
import { Button } from '../../../shared/components/ui/Button'
import { useUpdateIntegraciones } from '../hooks/useIntegraciones'

interface GoogleCalendarConfigProps {
  hasGoogle: boolean
  googleCalendarId: string
}

export function GoogleCalendarConfig({ hasGoogle, googleCalendarId }: GoogleCalendarConfigProps) {
  const [refreshToken, setRefreshToken] = useState('')
  const [calendarId, setCalendarId] = useState(googleCalendarId)
  const { mutate, isPending } = useUpdateIntegraciones()

  function handleSave() {
    mutate(
      { google_refresh_token: refreshToken, google_calendar_id: calendarId },
      { onSuccess: () => setRefreshToken('') },
    )
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-title-lg font-semibold">Google Calendar</h2>
        <Badge variant={hasGoogle ? 'success' : 'neutral'}>{hasGoogle ? 'Conectado' : 'Desconectado'}</Badge>
      </div>
      <Input
        label="Refresh token"
        type="password"
        value={refreshToken}
        onChange={(e) => setRefreshToken(e.target.value)}
        placeholder="Se genera desde Google Cloud Console"
      />
      <Input label="Calendar ID" value={calendarId} onChange={(e) => setCalendarId(e.target.value)} />
      <Button
        type="button"
        onClick={handleSave}
        disabled={!refreshToken}
        loading={isPending}
        className="self-start"
      >
        Guardar
      </Button>
    </div>
  )
}
