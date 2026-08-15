import { useEffect, useState } from 'react'
import { Button } from '../../../shared/components/ui/Button'

interface CredencialesGeneradasProps {
  apiKey: string
  telegramSecretToken: string
  onConfirm: () => void
}

function CredentialField({ label, icon, value }: { label: string; icon: string; value: string }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex flex-col gap-1">
      <span className="text-label-md font-medium text-on-surface-variant">
        {icon} {label}
      </span>
      <div className="flex items-center gap-2">
        <input
          readOnly
          value={value}
          aria-label={label}
          className="flex-1 rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-body-md"
        />
        <Button type="button" variant="outline" onClick={handleCopy}>
          {copied ? '¡Copiado!' : 'Copiar'}
        </Button>
      </div>
    </div>
  )
}

export function CredencialesGeneradas({ apiKey, telegramSecretToken, onConfirm }: CredencialesGeneradasProps) {
  useEffect(() => {
    function handleBeforeUnload(e: BeforeUnloadEvent) {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-on-surface/40 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-xl bg-surface-container-lowest p-6 shadow-sm">
        <h2 className="mb-4 text-center text-headline-sm font-semibold">¡Profesional creado con éxito!</h2>
        <p role="alert" className="mb-6 rounded-lg bg-error-container px-3 py-2 text-label-md text-error">
          ⚠️ Estas credenciales se muestran UNA SOLA VEZ. Copialas antes de cerrar esta ventana.
        </p>
        <div className="flex flex-col gap-4">
          <CredentialField label="API Key" icon="🔑" value={apiKey} />
          <CredentialField label="Telegram Secret Token" icon="✈️" value={telegramSecretToken} />
        </div>
        <Button type="button" onClick={onConfirm} className="mt-6 w-full">
          Ya copié las credenciales
        </Button>
      </div>
    </div>
  )
}
