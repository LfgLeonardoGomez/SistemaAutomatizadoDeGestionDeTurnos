interface HeaderProps {
  onLogout?: () => void
}

export function Header({ onLogout }: HeaderProps) {
  return (
    <header className="flex h-14 items-center justify-between border-b border-outline-variant bg-surface-container-lowest px-6">
      <span className="text-title-lg font-semibold">Panel del Profesional</span>
      <button
        type="button"
        onClick={onLogout}
        aria-label="Cerrar sesión"
        className="flex items-center gap-1 text-body-md font-medium text-on-surface-variant hover:text-error"
      >
        <span className="material-symbols-outlined" aria-hidden="true">
          exit_to_app
        </span>
        Cerrar sesión
      </button>
    </header>
  )
}
