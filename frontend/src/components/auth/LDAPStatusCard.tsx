import { useState } from 'react'
import { api } from '../../services/api'

interface LDAPStatus {
  connected: boolean
  server: string
  error: string | null
}

export function LDAPStatusCard() {
  const [status, setStatus] = useState<LDAPStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<string | null>(null)

  async function checkStatus() {
    setLoading(true)
    setStatus(null)
    try {
      const { data } = await api.get<LDAPStatus>('/api/admin/ldap/status/')
      setStatus(data)
    } catch {
      setStatus({ connected: false, server: '', error: 'Non disponibile' })
    } finally {
      setLoading(false)
    }
  }

  async function runSync() {
    setSyncing(true)
    setSyncResult(null)
    try {
      const { data } = await api.post<{ message?: string; output?: string }>('/api/admin/ldap/sync/')
      setSyncResult(data.output ?? data.message ?? 'Sync completato')
    } catch (err: unknown) {
      const res = (err as { response?: { data?: { detail?: string } } })?.response
      setSyncResult(res?.data?.detail ?? 'Errore durante la sincronizzazione')
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="font-medium text-slate-800">Stato LDAP</h3>
      <p className="mt-1 text-sm text-slate-600">
        Connessione e sincronizzazione utenti da Active Directory / LDAP.
      </p>
      <div className="mt-4 flex items-center gap-2">
        <span
          className={`inline-block h-3 w-3 rounded-full ${
            status ? (status.connected ? 'bg-green-500' : 'bg-red-500') : 'bg-slate-300'
          }`}
        />
        <span className="text-sm text-slate-600">
          {loading ? 'Verifica...' : status?.error ?? (status?.connected ? 'Connesso' : 'Non verificato')}
        </span>
      </div>
      {status?.server && <p className="mt-1 text-xs text-slate-500">Server: {status.server}</p>}
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={checkStatus}
          disabled={loading}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          Testa connessione
        </button>
        <button
          type="button"
          onClick={runSync}
          disabled={syncing}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {syncing ? 'Sincronizzazione...' : 'Sincronizza utenti'}
        </button>
      </div>
      {syncResult && (
        <pre className="mt-3 rounded bg-slate-50 p-2 text-xs text-slate-700">{syncResult}</pre>
      )}
    </div>
  )
}
