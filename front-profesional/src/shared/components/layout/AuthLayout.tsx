import { Outlet } from 'react-router-dom'

export function AuthLayout() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-background px-4">
      <div className="flex flex-col items-center gap-2 text-center">
        <span className="text-headline-lg font-semibold text-primary">Sistema de Gestión de Turnos</span>
        <span className="text-label-md font-medium uppercase tracking-wide text-on-surface-variant">
          Panel del Profesional
        </span>
      </div>
      <Outlet />
      <p className="text-label-sm text-on-surface-variant">© 2026 Sistema de Gestión de Turnos</p>
    </div>
  )
}
