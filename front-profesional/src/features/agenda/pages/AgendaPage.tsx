import { useState } from 'react'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { CalendarView } from '../components/CalendarView'
import { SlotList } from '../components/SlotList'
import { AppointmentModal } from '../components/AppointmentModal'
import { useDisponibilidad } from '../hooks/useDisponibilidad'

export default function AgendaPage() {
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [pendingSlot, setPendingSlot] = useState<string | null>(null)
  const fecha = format(selectedDate, 'yyyy-MM-dd')
  const { slots, isLoading, disponiblesCount, ocupadosCount } = useDisponibilidad(fecha)

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-headline-lg font-semibold">Agenda</h1>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <CalendarView selectedDate={selectedDate} onSelectDate={setSelectedDate} />
        <div className="flex flex-col gap-3">
          <div>
            <h2 className="text-title-lg font-semibold capitalize">
              {format(selectedDate, "EEEE, d 'de' MMMM", { locale: es })}
            </h2>
            {!isLoading && (
              <p className="text-body-md text-on-surface-variant">
                {ocupadosCount} ocupados · {disponiblesCount} disponibles
              </p>
            )}
          </div>
          {isLoading ? <Skeleton count={4} /> : <SlotList slots={slots} onAgendar={setPendingSlot} />}
        </div>
      </div>

      {pendingSlot && (
        <AppointmentModal
          isOpen
          fecha={fecha}
          horaInicio={pendingSlot}
          onClose={() => setPendingSlot(null)}
          onSuccess={() => setPendingSlot(null)}
        />
      )}
    </div>
  )
}
