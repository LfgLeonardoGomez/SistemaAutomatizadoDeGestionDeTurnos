import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background text-on-surface">
      <p className="text-label-sm font-semibold text-on-surface-variant">404</p>
      <h1 className="text-headline-md font-semibold">Página no encontrada</h1>
      <Link to="/" className="text-primary underline">
        Volver al inicio
      </Link>
    </div>
  )
}
