export function Skeleton({ count = 1, className = 'h-16 w-full' }: { count?: number; className?: string }) {
  return (
    <div role="status" aria-label="Cargando" className="flex flex-col gap-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={`animate-pulse rounded-lg bg-surface-container ${className}`} />
      ))}
    </div>
  )
}
