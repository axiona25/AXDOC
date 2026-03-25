import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  createSecurityIncident,
  fetchSecurityIncidents,
  updateSecurityIncident,
  type SecurityIncident,
  type SecurityIncidentPayload,
} from '../services/securityService'
import { IncidentFormModal } from '../components/security/IncidentFormModal'

const severityBadge: Record<string, string> = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200',
  critical: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200',
}

export function SecurityIncidentsPage() {
  const [rows, setRows] = useState<SecurityIncident[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [severity, setSeverity] = useState('')
  const [st, setSt] = useState('')
  const [category, setCategory] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<SecurityIncident | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchSecurityIncidents({
        ...(severity ? { severity } : {}),
        ...(st ? { status: st } : {}),
        ...(category ? { category } : {}),
      })
      setRows(data.results)
      setCount(data.count)
    } catch {
      setRows([])
      setCount(0)
    } finally {
      setLoading(false)
    }
  }, [severity, st, category])

  useEffect(() => {
    void load()
  }, [load])

  const openNew = () => {
    setEditing(null)
    setModalOpen(true)
  }

  const openEdit = (row: SecurityIncident) => {
    setEditing(row)
    setModalOpen(true)
  }

  const handleSave = async (payload: SecurityIncidentPayload) => {
    if (editing) {
      await updateSecurityIncident(editing.id, payload)
    } else {
      await createSecurityIncident(payload)
    }
    await load()
  }

  return (
    <div className="p-6">
      <Link to="/dashboard" className="text-sm text-indigo-600 hover:underline dark:text-indigo-400">
        ← Dashboard
      </Link>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Incidenti di sicurezza</h1>
        <button
          type="button"
          onClick={openNew}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 dark:hover:bg-indigo-500"
        >
          Nuovo incidente
        </button>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
          aria-label="Filtra per severità"
        >
          <option value="">Severità (tutte)</option>
          <option value="low">Basso</option>
          <option value="medium">Medio</option>
          <option value="high">Alto</option>
          <option value="critical">Critico</option>
        </select>
        <select
          value={st}
          onChange={(e) => setSt(e.target.value)}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
          aria-label="Filtra per stato"
        >
          <option value="">Stato (tutti)</option>
          <option value="open">Aperto</option>
          <option value="investigating">In indagine</option>
          <option value="mitigated">Mitigato</option>
          <option value="resolved">Risolto</option>
          <option value="closed">Chiuso</option>
        </select>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
          aria-label="Filtra per categoria"
        >
          <option value="">Categoria (tutte)</option>
          <option value="data_breach">Violazione dati</option>
          <option value="unauthorized_access">Accesso non autorizzato</option>
          <option value="other">Altro</option>
        </select>
      </div>

      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{count} incidenti</p>

      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
        <table className="min-w-full text-left text-sm" aria-label="Elenco incidenti di sicurezza">
          <thead className="bg-slate-50 dark:bg-slate-800/80">
            <tr>
              <th scope="col" className="px-3 py-2 font-medium text-slate-700 dark:text-slate-200">
                Severità
              </th>
              <th scope="col" className="px-3 py-2 font-medium text-slate-700 dark:text-slate-200">
                Titolo
              </th>
              <th scope="col" className="px-3 py-2 font-medium text-slate-700 dark:text-slate-200">
                Categoria
              </th>
              <th scope="col" className="px-3 py-2 font-medium text-slate-700 dark:text-slate-200">
                Stato
              </th>
              <th scope="col" className="px-3 py-2 font-medium text-slate-700 dark:text-slate-200">
                Rilevato
              </th>
              <th scope="col" className="px-3 py-2 font-medium text-slate-700 dark:text-slate-200">
                Assegnato
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-slate-500 dark:text-slate-400">
                  Caricamento…
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-slate-500 dark:text-slate-400">
                  Nessun incidente.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr
                  key={r.id}
                  className="cursor-pointer border-t border-slate-100 hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-800/50"
                  onClick={() => openEdit(r)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      openEdit(r)
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  aria-label={`Apri dettaglio ${r.title}`}
                >
                  <td className="px-3 py-2">
                    <span
                      className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${severityBadge[r.severity] || ''}`}
                    >
                      {r.severity}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-slate-800 dark:text-slate-100">{r.title}</td>
                  <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{r.category}</td>
                  <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{r.status}</td>
                  <td className="px-3 py-2 text-slate-500 dark:text-slate-400">
                    {new Date(r.detected_at).toLocaleString('it-IT')}
                  </td>
                  <td className="px-3 py-2 text-slate-500 dark:text-slate-400">
                    {r.assigned_to_email || '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <IncidentFormModal
        open={modalOpen}
        initial={editing}
        onClose={() => setModalOpen(false)}
        onSave={handleSave}
      />
    </div>
  )
}
