import { useMemo, useState } from 'react'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { EmptyState } from '../../../shared/components/ui/EmptyState'
import { PacienteTable } from '../components/PacienteTable'
import { usePacientes } from '../hooks/usePacientes'

export default function PacientesListPage() {
  const { data, isLoading } = usePacientes()
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    const pacientes = data ?? []
    const query = search.trim().toLowerCase()
    if (!query) return pacientes
    return pacientes.filter(
      (p) =>
        p.nombre.toLowerCase().includes(query) ||
        p.apellido.toLowerCase().includes(query) ||
        p.dni.includes(query),
    )
  }, [data, search])

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-headline-lg font-semibold">Pacientes</h1>
        <p className="text-body-md text-on-surface-variant">Consultá los pacientes registrados en tu consultorio</p>
      </div>

      <input
        type="search"
        placeholder="Buscar por nombre, apellido o DNI..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full max-w-sm rounded-lg border border-outline-variant px-3 py-2 text-body-md outline-none focus:border-primary"
      />

      {isLoading ? (
        <Skeleton count={6} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title={data && data.length > 0 ? 'Sin resultados' : 'Sin pacientes aún'}
          description={
            data && data.length > 0
              ? 'No hay pacientes que coincidan con la búsqueda.'
              : 'Todavía no se registró ningún paciente.'
          }
        />
      ) : (
        <PacienteTable pacientes={filtered} />
      )}
    </div>
  )
}
