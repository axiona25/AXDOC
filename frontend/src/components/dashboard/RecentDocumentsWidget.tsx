import type { RecentDocumentItem } from '../../services/dashboardService'

const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Bozza',
  IN_REVIEW: 'In revisione',
  APPROVED: 'Approvato',
  REJECTED: 'Rifiutato',
  ARCHIVED: 'Archiviato',
}

interface RecentDocumentsWidgetProps {
  documents: RecentDocumentItem[]
  onSelectDocument?: (id: string) => void
}

export function RecentDocumentsWidget({ documents, onSelectDocument }: RecentDocumentsWidgetProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
      <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Documenti recenti</h3>
      <div className="mt-3 overflow-x-auto">
        {documents.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">Nessun documento</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-600 dark:border-slate-600 dark:text-slate-400">
                <th className="pb-2 pr-2 font-medium">Titolo</th>
                <th className="pb-2 pr-2 font-medium">Stato</th>
                <th className="pb-2 pr-2 font-medium">Modificato</th>
                <th className="pb-2 font-medium">Autore</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((d) => (
                <tr
                  key={d.id}
                  className="border-b border-slate-100 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-700/50"
                  role={onSelectDocument ? 'button' : undefined}
                  onClick={() => onSelectDocument?.(d.id)}
                >
                  <td className="py-2 pr-2 font-medium text-slate-800 dark:text-slate-100">{d.title}</td>
                  <td className="py-2 pr-2 text-slate-600 dark:text-slate-300">{STATUS_LABELS[d.status] || d.status}</td>
                  <td className="py-2 pr-2 text-slate-500 dark:text-slate-400">
                    {new Date(d.updated_at).toLocaleDateString('it-IT')}
                  </td>
                  <td className="py-2 text-slate-500 dark:text-slate-400">{d.created_by_email || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
