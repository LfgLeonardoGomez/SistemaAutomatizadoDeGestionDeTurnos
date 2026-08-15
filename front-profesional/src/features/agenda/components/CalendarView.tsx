import { useState } from 'react'
import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  startOfMonth,
  startOfWeek,
  subMonths,
} from 'date-fns'
import { es } from 'date-fns/locale'

const WEEKDAY_LABELS = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do']

interface CalendarViewProps {
  selectedDate: Date
  onSelectDate: (date: Date) => void
}

export function CalendarView({ selectedDate, onSelectDate }: CalendarViewProps) {
  const [visibleMonth, setVisibleMonth] = useState(selectedDate)

  const gridStart = startOfWeek(startOfMonth(visibleMonth), { weekStartsOn: 1 })
  const gridEnd = endOfWeek(endOfMonth(visibleMonth), { weekStartsOn: 1 })
  const days = eachDayOfInterval({ start: gridStart, end: gridEnd })

  return (
    <div className="rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
      <div className="mb-3 flex items-center justify-between">
        <button
          type="button"
          aria-label="Mes anterior"
          onClick={() => setVisibleMonth((m) => subMonths(m, 1))}
          className="rounded-full p-1 text-on-surface-variant hover:bg-surface-container"
        >
          <span className="material-symbols-outlined" aria-hidden="true">
            chevron_left
          </span>
        </button>
        <span className="text-title-lg font-semibold capitalize">
          {format(visibleMonth, 'MMMM yyyy', { locale: es })}
        </span>
        <button
          type="button"
          aria-label="Mes siguiente"
          onClick={() => setVisibleMonth((m) => addMonths(m, 1))}
          className="rounded-full p-1 text-on-surface-variant hover:bg-surface-container"
        >
          <span className="material-symbols-outlined" aria-hidden="true">
            chevron_right
          </span>
        </button>
      </div>
      <div className="grid grid-cols-7 gap-1 text-center text-label-sm text-on-surface-variant">
        {WEEKDAY_LABELS.map((label) => (
          <span key={label} className="py-1">
            {label}
          </span>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {days.map((day) => {
          const isCurrentMonth = isSameMonth(day, visibleMonth)
          const isSelected = isSameDay(day, selectedDate)
          return (
            <button
              key={day.toISOString()}
              type="button"
              onClick={() => onSelectDate(day)}
              disabled={!isCurrentMonth}
              className={`aspect-square rounded-lg text-body-md ${
                !isCurrentMonth
                  ? 'text-on-surface-variant/30'
                  : isSelected
                    ? 'bg-primary-container text-on-primary-container font-semibold'
                    : 'hover:bg-surface-container'
              }`}
            >
              {day.getDate()}
            </button>
          )
        })}
      </div>
    </div>
  )
}
