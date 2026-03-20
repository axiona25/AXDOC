import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getAuditLog } from '../services/auditService'
import type { AuditLogItem } from '../services/auditService'

const ACTION_LABELS: Record<string, string> = {
  LOGIN: 'Accesso',
  LOGOUT: 'Disconnessione',
  DOCUMENT_CREATED: 'Documento creato',
  DOCUMENT_UPDATED: 'Documento aggiornato',
  DOCUMENT_DOWNLOADED: 'Documento scaricato',
  WORKFLOW_STARTED: 'Workflow avviato',
  WORKFLOW_APPROVED: 'Workflow approvato',
  WORKFLOW_REJECTED: 'Workflow rifiutato',
}

export function AuditPage() {
  const [items, setItems] = useState<AuditLogItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getAuditLog({ page, page_size: 20 })
      .then((r) => {
        setItems(r.results ?? [])
        setTotal(r.count ?? 0)
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [page])

  return (
    <div className="mx-auto max-w-4xl p-4 md:p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-800">Registro attività</h1>
        <Link to="/dashboard" className="text-indigo-600 hover:underline">← Dashboard</Link>
      </div>
      {loading ? (
        <p className="text-slate-500">Caricamento...</p>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white shadow">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-slate-600">
                <th className="p-3 font-medium">Data</th>
                <th className="p-3 font-medium">Utente</th>
                <th className="p-3 font-medium">Azione</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id} className="border-b border-slate-100">
                  <td className="p-3 text-slate-600">
                    {new Date(a.timestamp).toLocaleString('it-IT')}
                  </td>
                  <td className="p-3 text-slate-800">{a.user_email || '—'}</td>
                  <td className="p-3 text-slate-700">{ACTION_LABELS[a.action] || a.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {total > 20 && (
            <div className="flex justify-center gap-2 border-t border-slate-200 p-3">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded border border-slate-300 px-3 py-1 disabled:opacity-50"
              >
                Precedente
              </button>
              <span className="py-1 text-slate-600">Pagina {page}</span>
              <button
                type="button"
                disabled={page * 20 >= total}
                onClick={() => setPage((p) => p + 1)}
                className="rounded border border-slate-300 px-3 py-1 disabled:opacity-50"
              >
                Successiva
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
