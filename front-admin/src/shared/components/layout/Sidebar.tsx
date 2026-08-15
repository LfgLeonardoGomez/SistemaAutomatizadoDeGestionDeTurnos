import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/', label: 'Profesionales', icon: 'group' },
  { to: '/metricas', label: 'Métricas', icon: 'monitoring' },
] as const

export function Sidebar() {
  return (
    <nav
      aria-label="Navegación principal"
      className="flex w-[60px] flex-col items-center gap-2 border-r border-outline-variant bg-surface-container-lowest py-4"
    >
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          title={item.label}
          className={({ isActive }) =>
            `flex h-10 w-10 items-center justify-center rounded-lg text-on-surface-variant transition-colors ${
              isActive ? 'bg-primary-container text-on-primary-container' : 'hover:bg-surface-container'
            }`
          }
        >
          <span className="material-symbols-outlined" aria-hidden="true">
            {item.icon}
          </span>
          <span className="sr-only">{item.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
