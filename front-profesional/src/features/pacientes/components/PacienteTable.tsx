import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import type { Paciente } from '../../../shared/types'

export function PacienteTable({ pacientes }: { pacientes: Paciente[] }) {
  return (
    <table className="w-full text-left text-body-md">
      <thead>
        <tr className="border-b border-outline-variant text-label-md text-on-surface-variant">
          <th className="py-2 pr-4 font-medium">Nombre</th>
          <th className="py-2 pr-4 font-medium">DNI</th>
          <th className="py-2 pr-4 font-medium">Teléfono</th>
          <th className="py-2 pr-4 font-medium">Registrado</th>
        </tr>
      </thead>
      <tbody>
        {pacientes.map((paciente) => (
          <tr key={paciente.id} className="border-b border-outline-variant last:border-0 hover:bg-surface-container-low">
            <td className="py-3 pr-4">
              <Link to={`/pacientes/${paciente.id}`} className="font-medium text-primary hover:underline">
                {paciente.nombre} {paciente.apellido}
              </Link>
            </td>
            <td className="py-3 pr-4">{paciente.dni}</td>
            <td className="py-3 pr-4">{paciente.telefono}</td>
            <td className="py-3 pr-4">{format(new Date(paciente.creado_en), 'dd/MM/yyyy')}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
