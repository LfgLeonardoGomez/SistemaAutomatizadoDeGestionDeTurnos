import { format } from 'date-fns'
import { EstadoBadge } from '../../../shared/components/turno/EstadoBadge'
import { EmptyState } from '../../../shared/components/ui/EmptyState'
import type { Turno } from '../../../shared/types'

export function HistorialTurnos({ turnos }: { turnos: Turno[] }) {
  if (turnos.length === 0) {
    return <EmptyState title="Sin turnos registrados" description="Este paciente todavía no tuvo turnos." />
  }

  const ordenados = [...turnos].sort((a, b) => b.fecha.localeCompare(a.fecha) || b.hora_inicio.localeCompare(a.hora_inicio))

  return (
    <table className="w-full text-left text-body-md">
      <thead>
        <tr className="border-b border-outline-variant text-label-md text-on-surface-variant">
          <th className="py-2 pr-4 font-medium">Fecha</th>
          <th className="py-2 pr-4 font-medium">Hora</th>
          <th className="py-2 pr-4 font-medium">Estado</th>
        </tr>
      </thead>
      <tbody>
        {ordenados.map((turno) => (
          <tr key={turno.id} className="border-b border-outline-variant last:border-0">
            <td className="py-3 pr-4">{format(new Date(`${turno.fecha}T00:00:00`), 'dd/MM/yyyy')}</td>
            <td className="py-3 pr-4">
              {turno.hora_inicio}–{turno.hora_fin}
            </td>
            <td className="py-3 pr-4">
              <EstadoBadge estado={turno.estado} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
