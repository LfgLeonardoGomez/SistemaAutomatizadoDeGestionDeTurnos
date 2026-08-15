const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'] as const

interface DiasSelectorProps {
  selected: string[]
  onChange: (dias: string[]) => void
}

export function DiasSelector({ selected, onChange }: DiasSelectorProps) {
  function toggle(dia: string) {
    if (selected.includes(dia)) {
      onChange(selected.filter((d) => d !== dia))
    } else {
      onChange([...selected, dia])
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {DIAS.map((dia) => {
        const isSelected = selected.includes(dia)
        return (
          <button
            key={dia}
            type="button"
            aria-pressed={isSelected}
            onClick={() => toggle(dia)}
            className={`rounded-full px-3 py-1 text-label-md font-semibold transition-colors ${
              isSelected
                ? 'bg-primary text-on-primary'
                : 'border border-outline-variant text-on-surface-variant hover:bg-surface-container'
            }`}
          >
            {dia}
          </button>
        )
      })}
    </div>
  )
}
