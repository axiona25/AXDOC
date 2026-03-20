import type { AuditLogItem } from '../../services/auditService'

const ACTION_LABELS: Record<string, string> = {
  DOCUMENT_CREATED: 'Documento creato',
  DOCUMENT_UPLOADED: 'Nuova versione caricata',
  DOCUMENT_DOWNLOADED: 'Documento scaricato',
  DOCUMENT_DELETED: 'Documento eliminato',
  DOCUMENT_SHARED: 'Documento condiviso',
  WORKFLOW_STARTED: 'Workflow avviato',
  WORKFLOW_APPROVED: 'Documento approvato',
  WORKFLOW_REJECTED: 'Documento rifiutato',
  LOGIN: 'Accesso',
  LOGOUT: 'Uscita',
}

function labelFor(log: AuditLogItem): string {
  const base = ACTION_LABELS[log.action] || log.action
  const version = log.detail?.version as number | undefined
  if (log.action === 'DOCUMENT_UPLOADED' && version) return `Versione ${version} caricata`
  return base
}

export function ActivityTimeline({ items }: { items: AuditLogItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">Nessuna attività recente.</p>
  }
  return (
    <ul className="space-y-3">
      {items.map((log) => (
        <li key={log.id} className="flex gap-3 border-l-2 border-slate-200 pl-3">
          <div className="flex-1">
            <p className="text-sm text-slate-800">
              <span className="font-medium">{log.user_email || 'Sistema'}</span>
              {' — '}
              {labelFor(log)}
            </p>
            <p className="text-xs text-slate-500">
              {new Date(log.timestamp).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' })}
            </p>
          </div>
        </li>
      ))}
    </ul>
  )
}
