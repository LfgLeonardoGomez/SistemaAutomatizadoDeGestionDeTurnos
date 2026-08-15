import { useMemo, useState } from 'react'
import { Skeleton } from '../../../shared/components/ui/Skeleton'
import { EmptyState } from '../../../shared/components/ui/EmptyState'
import { Button } from '../../../shared/components/ui/Button'
import { ConfirmDialog } from '../../../shared/components/ui/ConfirmDialog'
import { ProfesionalTable } from '../components/ProfesionalTable'
import { CreateProfesionalModal } from '../components/CreateProfesionalModal'
import { CredencialesGeneradas } from '../components/CredencialesGeneradas'
import { useProfesionales } from '../hooks/useProfesionales'
import { useToggleProfesionalActive } from '../hooks/useToggleProfesionalActive'
import type { ProfesionalAdminResponse, ProfesionalCreateResponse } from '../../../shared/types'

const PAGE_SIZE = 10

export default function ProfesionalesListPage() {
  const { data, isLoading } = useProfesionales()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [createdCredentials, setCreatedCredentials] = useState<ProfesionalCreateResponse | null>(null)
  const [pendingToggle, setPendingToggle] = useState<ProfesionalAdminResponse | null>(null)
  const toggleActive = useToggleProfesionalActive()

  const filtered = useMemo(() => {
    const profesionales = data ?? []
    const query = search.trim().toLowerCase()
    if (!query) return profesionales
    return profesionales.filter(
      (p) => p.nombre.toLowerCase().includes(query) || p.email.toLowerCase().includes(query),
    )
  }, [data, search])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const pageItems = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)
  const rangeStart = filtered.length === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1
  const rangeEnd = Math.min(currentPage * PAGE_SIZE, filtered.length)

  function handleSearchChange(value: string) {
    setSearch(value)
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-headline-sm font-semibold">Profesionales</h1>
          <p className="text-body-md text-on-surface-variant">Gestión de especialistas registrados</p>
        </div>
        <Button type="button" onClick={() => setIsCreateModalOpen(true)}>
          + Nuevo profesional
        </Button>
      </div>

      <input
        type="search"
        placeholder="Buscar por nombre o email..."
        value={search}
        onChange={(e) => handleSearchChange(e.target.value)}
        className="w-full max-w-sm rounded-lg border border-outline-variant px-3 py-2 text-body-md outline-none focus:border-primary"
      />

      {isLoading ? (
        <Skeleton count={6} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title={data && data.length > 0 ? 'Sin resultados' : 'Sin profesionales aún'}
          description={
            data && data.length > 0
              ? 'No hay profesionales que coincidan con la búsqueda.'
              : 'Todavía no se registró ningún profesional.'
          }
        />
      ) : (
        <>
          <ProfesionalTable profesionales={pageItems} onToggleActive={setPendingToggle} />
          <div className="flex items-center justify-between text-label-md text-on-surface-variant">
            <span>
              Mostrando {rangeStart} a {rangeEnd} de {filtered.length} profesionales
            </span>
            <div className="flex items-center gap-1">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setPage(n)}
                  aria-current={n === currentPage ? 'page' : undefined}
                  className={`h-8 w-8 rounded-lg text-label-md font-semibold ${
                    n === currentPage
                      ? 'bg-primary text-on-primary'
                      : 'text-on-surface-variant hover:bg-surface-container'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      <CreateProfesionalModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={(created) => {
          setIsCreateModalOpen(false)
          setCreatedCredentials(created)
        }}
      />

      {createdCredentials && (
        <CredencialesGeneradas
          apiKey={createdCredentials.api_key}
          telegramSecretToken={createdCredentials.telegram_secret_token}
          onConfirm={() => setCreatedCredentials(null)}
        />
      )}

      <ConfirmDialog
        isOpen={pendingToggle !== null}
        message={`¿Estás seguro de ${pendingToggle?.is_active ? 'desactivar' : 'activar'} a ${pendingToggle?.nombre}?`}
        confirmLabel={pendingToggle?.is_active ? 'Desactivar' : 'Activar'}
        isLoading={toggleActive.isPending}
        onCancel={() => setPendingToggle(null)}
        onConfirm={() => {
          if (!pendingToggle) return
          toggleActive.mutate(
            { id: pendingToggle.id, activate: !pendingToggle.is_active },
            { onSuccess: () => setPendingToggle(null) },
          )
        }}
      />
    </div>
  )
}
