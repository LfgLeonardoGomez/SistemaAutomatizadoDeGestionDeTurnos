import { Link, useParams } from 'react-router-dom'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { HistorialTurnos } from '../components/HistorialTurnos'
import { usePaciente } from '../hooks/usePaciente'

function isNotFoundError(error: unknown): boolean {
  return Boolean(
    error && typeof error === 'object' && 'response' in error &&
      (error as { response?: { status?: number } }).response?.status === 404,
  )
}

export default function PacienteDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data, isLoading, isError, error } = usePaciente(Number(id))

  if (isLoading) {
    return <Skeleton count={4} />
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <p className="text-title-lg font-semibold">
          {isNotFoundError(error) ? 'Paciente no encontrado' : 'No se pudo cargar el paciente'}
        </p>
        <Link to="/pacientes" className="text-primary underline">
          Volver al listado
        </Link>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-headline-lg font-semibold">Detalle de paciente</h1>
      <div className="max-w-md rounded-xl border border-outline-variant bg-surface-container-lowest p-6">
        <div className="flex flex-col gap-4 text-body-md">
          <div>
            <span className="block text-label-md text-on-surface-variant">Nombre</span>
            <span className="font-medium">
              {data.nombre} {data.apellido}
            </span>
          </div>
          <div>
            <span className="block text-label-md text-on-surface-variant">DNI</span>
            <span>{data.dni}</span>
          </div>
          <div>
            <span className="block text-label-md text-on-surface-variant">Teléfono</span>
            <span>{data.telefono}</span>
          </div>
        </div>
      </div>

      <div>
        <h2 className="mb-2 text-title-lg font-semibold">Historial de turnos</h2>
        <HistorialTurnos turnos={data.turnos} />
      </div>

      <Link to="/pacientes" className="text-label-md font-medium text-primary hover:underline">
        ← Volver al listado
      </Link>
    </div>
  )
}
