import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: 'dashboard' },
  { to: '/agenda', label: 'Agenda', icon: 'calendar_month' },
  { to: '/pacientes', label: 'Pacientes', icon: 'group' },
  { to: '/configuracion', label: 'Configuración', icon: 'settings' },
  { to: '/metricas', label: 'Métricas', icon: 'monitoring' },
  { to: '/integraciones', label: 'Integraciones', icon: 'power_settings_new' },
] as const

export function Sidebar() {
  return (
    <nav
      aria-label="Navegación principal"
      className="flex w-60 flex-col gap-1 border-r border-outline-variant bg-surface-container-lowest p-4"
    >
      <span className="mb-4 px-2 text-headline-sm font-bold text-primary">SG Turnos</span>
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg border-l-4 px-3 py-2 text-body-md font-medium transition-colors ${
              isActive
                ? 'border-primary bg-primary-container/10 text-primary'
                : 'border-transparent text-on-surface-variant hover:bg-surface-container'
            }`
          }
        >
          <span className="material-symbols-outlined" aria-hidden="true">
            {item.icon}
          </span>
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}
