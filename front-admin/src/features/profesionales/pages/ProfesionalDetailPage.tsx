import { Link, useParams } from 'react-router-dom'
import { format } from 'date-fns'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { Badge } from '../../../shared/components/ui/Badge'
import { useProfesional } from '../hooks/useProfesional'

function isNotFoundError(error: unknown): boolean {
  return Boolean(
    error && typeof error === 'object' && 'response' in error &&
      (error as { response?: { status?: number } }).response?.status === 404,
  )
}

export default function ProfesionalDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data, isLoading, isError, error } = useProfesional(Number(id))

  if (isLoading) {
    return <Skeleton count={4} />
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <p className="text-title-lg font-semibold">
          {isNotFoundError(error) ? 'Profesional no encontrado' : 'No se pudo cargar el profesional'}
        </p>
        <Link to="/" className="text-primary underline">
          Volver al listado
        </Link>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-headline-sm font-semibold">Detalle de profesional</h1>
      <div className="max-w-md rounded-xl border border-outline-variant bg-surface-container-lowest p-6">
        <div className="flex flex-col gap-4 text-body-md">
          <div>
            <span className="block text-label-md text-on-surface-variant">Nombre</span>
            <span className="font-medium">{data.nombre}</span>
          </div>
          <div>
            <span className="block text-label-md text-on-surface-variant">Email</span>
            <span>{data.email}</span>
          </div>
          <div>
            <span className="block text-label-md text-on-surface-variant">Especialidad</span>
            <span>{data.especialidad}</span>
          </div>
          <div>
            <span className="block text-label-md text-on-surface-variant">Estado</span>
            <Badge variant={data.is_active ? 'success' : 'neutral'}>
              {data.is_active ? 'Activo' : 'Inactivo'}
            </Badge>
          </div>
          <div>
            <span className="block text-label-md text-on-surface-variant">Fecha de registro</span>
            <span>{format(new Date(data.creado_en), 'dd/MM/yyyy')}</span>
          </div>
        </div>
      </div>
      <Link to="/" className="text-label-md font-medium text-primary hover:underline">
        ← Volver al listado
      </Link>
    </div>
  )
}
