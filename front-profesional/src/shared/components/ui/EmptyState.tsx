interface EmptyStateProps {
  title: string
  description?: string
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-xl border border-dashed border-outline-variant py-16 text-center">
      <p className="text-title-lg font-semibold text-on-surface">{title}</p>
      {description && <p className="text-body-md text-on-surface-variant">{description}</p>}
    </div>
  )
}
