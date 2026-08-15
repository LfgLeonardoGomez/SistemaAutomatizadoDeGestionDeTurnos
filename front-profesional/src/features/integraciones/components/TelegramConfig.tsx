import { useState } from 'react'
import { Badge } from '../../../shared/components/ui/Badge'
import { Input } from '../../../shared/components/ui/Input'
import { Button } from '../../../shared/components/ui/Button'
import { useUpdateIntegraciones } from '../hooks/useIntegraciones'

export function TelegramConfig({ hasTelegram }: { hasTelegram: boolean }) {
  const [token, setToken] = useState('')
  const { mutate, isPending } = useUpdateIntegraciones()

  function handleSave() {
    mutate({ telegram_bot_token: token }, { onSuccess: () => setToken('') })
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-title-lg font-semibold">Telegram</h2>
        <Badge variant={hasTelegram ? 'success' : 'neutral'}>{hasTelegram ? 'Conectado' : 'Desconectado'}</Badge>
      </div>
      <Input
        label="Token del bot"
        type="password"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        placeholder="El token se obtiene de @BotFather"
      />
      <Button type="button" onClick={handleSave} disabled={!token} loading={isPending} className="self-start">
        Guardar token
      </Button>
    </div>
  )
}
