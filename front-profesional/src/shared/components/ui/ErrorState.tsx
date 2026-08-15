import { Button } from './Button'

interface ErrorStateProps {
  message?: string
  onRetry?: () => void
}

export function ErrorState({ message = 'Ocurrió un error. Intentá de nuevo.', onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-error-container bg-error-container/40 py-12 text-center">
      <p className="text-body-md text-error">{message}</p>
      {onRetry && (
        <Button type="button" variant="outline" onClick={onRetry}>
          Reintentar
        </Button>
      )}
    </div>
  )
}
