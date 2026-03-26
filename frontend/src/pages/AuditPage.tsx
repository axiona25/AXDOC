import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { FileSpreadsheet, FileText } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { getAuditLog } from '../services/auditService'
import type { AuditLogItem } from '../services/auditService'
import { exportAuditExcel, exportAuditPdf } from '../services/exportService'
import { announce } from '../components/common/ScreenReaderAnnouncer'

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
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === 'ADMIN'
  const [items, setItems] = useState<AuditLogItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [userId, setUserId] = useState('')
  const [actionFilter, setActionFilter] = useState('')

  useEffect(() => {
    setLoading(true)
    getAuditLog({
      page,
      page_size: 20,
      ...(dateFrom && { date_from: dateFrom }),
      ...(dateTo && { date_to: dateTo }),
      ...(userId.trim() && { user_id: userId.trim() }),
      ...(actionFilter.trim() && { action: actionFilter.trim() }),
    })
      .then((r) => {
        setItems(r.results ?? [])
        setTotal(r.count ?? 0)
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [page, dateFrom, dateTo, userId, actionFilter])

  const exportParams = (): Record<string, string | undefined> => ({
    ...(dateFrom && { date_from: dateFrom }),
    ...(dateTo && { date_to: dateTo }),
    ...(userId.trim() && { user_id: userId.trim() }),
    ...(actionFilter.trim() && { action: actionFilter.trim() }),
  })

  const totalPages = Math.max(1, Math.ceil(total / 20))

  const goPage = useCallback(
    (next: number) => {
      const p = Math.min(Math.max(1, next), totalPages)
      setPage(p)
      announce(`Pagina ${p} di ${totalPages}, ${total} risultati`)
    },
    [totalPages, total],
  )

  return (
    <div className="mx-auto max-w-4xl p-4 md:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Registro attività</h1>
        <Link to="/dashboard" className="text-indigo-600 hover:underline dark:text-indigo-400">
          ← Dashboard
        </Link>
      </div>

      <div className="mb-4 flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <div className="flex flex-wrap gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setPage(1)
              setDateFrom(e.target.value)
            }}
            className="rounded border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
            aria-label="Da data"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setPage(1)
              setDateTo(e.target.value)
            }}
            className="rounded border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
            aria-label="A data"
          />
          <input
            type="text"
            placeholder="ID utente (UUID)"
            value={userId}
            onChange={(e) => {
              setPage(1)
              setUserId(e.target.value)
            }}
            className="min-w-[180px] flex-1 rounded border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
          />
          <input
            type="text"
            placeholder="Codice azione (es. LOGIN)"
            value={actionFilter}
            onChange={(e) => {
              setPage(1)
              setActionFilter(e.target.value)
            }}
            className="min-w-[160px] flex-1 rounded border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
          />
        </div>
        {isAdmin && (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => exportAuditExcel(exportParams())}
              className="flex items-center gap-1.5 rounded bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
            >
              <FileSpreadsheet className="h-4 w-4" aria-hidden />
              Esporta Excel
            </button>
            <button
              type="button"
              onClick={() => exportAuditPdf(exportParams())}
              className="flex items-center gap-1.5 rounded bg-slate-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
            >
              <FileText className="h-4 w-4" aria-hidden />
              Esporta PDF
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <p className="text-slate-500 dark:text-slate-400">Caricamento...</p>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white shadow dark:border-slate-700 dark:bg-slate-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-slate-600 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-300">
                <th className="p-3 font-medium">Data</th>
                <th className="p-3 font-medium">Utente</th>
                <th className="p-3 font-medium">Azione</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id} className="border-b border-slate-100 dark:border-slate-700">
                  <td className="p-3 text-slate-600 dark:text-slate-400">
                    {new Date(a.timestamp).toLocaleString('it-IT')}
                  </td>
                  <td className="p-3 text-slate-800 dark:text-slate-100">{a.user_email || '—'}</td>
                  <td className="p-3 text-slate-700 dark:text-slate-200">{ACTION_LABELS[a.action] || a.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {total > 20 && (
            <div className="flex justify-center gap-2 border-t border-slate-200 p-3">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => goPage(page - 1)}
                className="rounded border border-slate-300 px-3 py-1 disabled:opacity-50"
              >
                Precedente
              </button>
              <span className="py-1 text-slate-600">Pagina {page}</span>
              <button
                type="button"
                disabled={page * 20 >= total}
                onClick={() => goPage(page + 1)}
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
