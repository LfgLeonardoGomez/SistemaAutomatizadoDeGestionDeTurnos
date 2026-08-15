import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import { Badge } from '../../../shared/components/ui/Badge'
import type { ProfesionalAdminResponse } from '../../../shared/types'

interface ProfesionalTableProps {
  profesionales: ProfesionalAdminResponse[]
  onToggleActive: (profesional: ProfesionalAdminResponse) => void
}

export function ProfesionalTable({ profesionales, onToggleActive }: ProfesionalTableProps) {
  return (
    <table className="w-full text-left text-body-md">
      <thead>
        <tr className="border-b border-outline-variant text-label-md text-on-surface-variant">
          <th className="py-2 pr-4 font-medium">ID</th>
          <th className="py-2 pr-4 font-medium">Nombre</th>
          <th className="py-2 pr-4 font-medium">Email</th>
          <th className="py-2 pr-4 font-medium">Especialidad</th>
          <th className="py-2 pr-4 font-medium">Estado</th>
          <th className="py-2 pr-4 font-medium">Fecha de registro</th>
          <th className="py-2 pr-4 font-medium">Acciones</th>
        </tr>
      </thead>
      <tbody>
        {profesionales.map((profesional) => (
          <tr
            key={profesional.id}
            className={`border-b border-outline-variant last:border-0 hover:bg-surface-container-low ${
              profesional.is_active ? '' : 'opacity-60'
            }`}
          >
            <td className="py-3 pr-4">#{profesional.id}</td>
            <td className="py-3 pr-4">
              <Link to={`/profesionales/${profesional.id}`} className="font-medium text-primary hover:underline">
                {profesional.nombre}
              </Link>
            </td>
            <td className="py-3 pr-4">{profesional.email}</td>
            <td className="py-3 pr-4">{profesional.especialidad}</td>
            <td className="py-3 pr-4">
              <Badge variant={profesional.is_active ? 'success' : 'neutral'}>
                {profesional.is_active ? 'Activo' : 'Inactivo'}
              </Badge>
            </td>
            <td className="py-3 pr-4">{format(new Date(profesional.creado_en), 'dd/MM/yyyy')}</td>
            <td className="py-3 pr-4">
              <button
                type="button"
                onClick={() => onToggleActive(profesional)}
                className={`text-label-md font-semibold ${
                  profesional.is_active ? 'text-error' : 'text-primary'
                }`}
              >
                {profesional.is_active ? 'Desactivar' : 'Activar'}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
