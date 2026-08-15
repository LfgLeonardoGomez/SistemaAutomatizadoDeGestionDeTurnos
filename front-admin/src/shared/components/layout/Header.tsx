interface HeaderProps {
  onLogout?: () => void
}

export function Header({ onLogout }: HeaderProps) {
  return (
    <header className="flex h-14 items-center justify-between border-b border-outline-variant bg-surface-container-lowest px-6">
      <span className="text-title-lg font-semibold">Admin Portal</span>
      <button
        type="button"
        onClick={onLogout}
        className="text-body-md font-medium text-on-surface-variant hover:text-error"
      >
        Cerrar sesión
      </button>
    </header>
  )
}
