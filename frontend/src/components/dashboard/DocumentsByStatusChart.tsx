interface DocumentsByStatusChartProps {
  documentsByStatus?: Record<string, number> | null
}

const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Bozza',
  IN_REVIEW: 'In revisione',
  APPROVED: 'Approvato',
  REJECTED: 'Rifiutato',
  ARCHIVED: 'Archiviato',
}

const STATUS_COLORS: Record<string, string> = {
  DRAFT: '#94a3b8',
  IN_REVIEW: '#f59e0b',
  APPROVED: '#22c55e',
  REJECTED: '#ef4444',
  ARCHIVED: '#64748b',
}

export function DocumentsByStatusChart({ documentsByStatus }: DocumentsByStatusChartProps) {
  const data = documentsByStatus
    ? Object.entries(documentsByStatus)
        .map(([status, count]) => ({ status, count, label: STATUS_LABELS[status] || status }))
        .filter((d) => d.count > 0)
        .sort((a, b) => b.count - a.count)
    : []
  const total = data.reduce((s, d) => s + d.count, 0)

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-800">Documenti per stato</h3>
      {data.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">Nessun dato</p>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap gap-4">
            {data.map(({ status, count, label }) => (
              <div key={status} className="flex items-center gap-2">
                <span
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: STATUS_COLORS[status] || '#94a3b8' }}
                />
                <span className="text-sm text-slate-700">
                  {label}: <strong>{count}</strong>
                </span>
              </div>
            ))}
          </div>
          <div className="mt-3 flex h-3 w-full overflow-hidden rounded-full bg-slate-100">
            {data.map(({ status, count }) => {
              const pct = total > 0 ? (count / total) * 100 : 0
              return (
                <div
                  key={status}
                  className="transition-all"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: STATUS_COLORS[status] || '#94a3b8',
                  }}
                  title={`${STATUS_LABELS[status] || status}: ${count}`}
                />
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
