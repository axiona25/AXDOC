import { Link } from 'react-router-dom'

interface ActivityItem {
  id: string
  user_email: string | null
  action: string
  detail: Record<string, unknown>
  timestamp: string
}

interface RecentActivityFeedProps {
  items: ActivityItem[]
}

const ACTION_LABELS: Record<string, string> = {
  LOGIN: 'Accesso',
  LOGOUT: 'Disconnessione',
  DOCUMENT_CREATED: 'Documento creato',
  DOCUMENT_UPDATED: 'Documento aggiornato',
  DOCUMENT_DOWNLOADED: 'Documento scaricato',
  WORKFLOW_STARTED: 'Workflow avviato',
  WORKFLOW_APPROVED: 'Workflow approvato',
  WORKFLOW_REJECTED: 'Workflow rifiutato',
  CALL_ENDED: 'Chiamata terminata',
}

function formatRelative(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const mins = Math.floor(diffMs / 60000)
  const hours = Math.floor(diffMs / 3600000)
  const days = Math.floor(diffMs / 86400000)
  if (mins < 1) return 'ora'
  if (mins < 60) return `${mins} min fa`
  if (hours < 24) return `${hours} h fa`
  if (days < 7) return `${days} gg fa`
  return d.toLocaleDateString('it-IT')
}

export function RecentActivityFeed({ items }: RecentActivityFeedProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Attività recente</h3>
        <Link to="/audit" className="text-xs text-indigo-600 hover:underline dark:text-indigo-400">
          Vedi tutto
        </Link>
      </div>
      <ul className="mt-3 space-y-2">
        {items.length === 0 ? (
          <li className="text-sm text-slate-500 dark:text-slate-400">Nessuna attività</li>
        ) : (
          items.map((a) => (
            <li
              key={a.id}
              className="flex items-start gap-2 rounded-lg bg-slate-50 px-2 py-1.5 text-sm dark:bg-slate-700/50"
            >
              <span className="font-medium text-slate-700 dark:text-slate-200">{a.user_email || 'Sistema'}</span>
              <span className="text-slate-600 dark:text-slate-300">{ACTION_LABELS[a.action] || a.action}</span>
              <span className="ml-auto text-xs text-slate-400 dark:text-slate-500">{formatRelative(a.timestamp)}</span>
            </li>
          ))
        )}
      </ul>
    </div>
  )
}
