import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getSettings, testEmail, testLdap } from '../services/adminService'
import type { SystemSettingsData } from '../services/adminService'

type TabId = 'email' | 'organization' | 'security' | 'storage' | 'ldap' | 'conservation'

const TABS: { id: TabId; label: string }[] = [
  { id: 'email', label: 'Email' },
  { id: 'organization', label: 'Organizzazione' },
  { id: 'security', label: 'Sicurezza' },
  { id: 'storage', label: 'Storage' },
  { id: 'ldap', label: 'LDAP' },
  { id: 'conservation', label: 'Conservazione' },
]

export function SettingsPage() {
  const [data, setData] = useState<SystemSettingsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<TabId>('email')
  const [message, setMessage] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const [testingEmail, setTestingEmail] = useState(false)
  const [testingLdap, setTestingLdap] = useState(false)

  useEffect(() => {
    getSettings()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  const handleTestEmail = async () => {
    setTestingEmail(true)
    setMessage(null)
    try {
      const res = await testEmail()
      setMessage({ type: 'ok', text: res.detail || 'Email inviata.' })
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setMessage({ type: 'err', text: err?.response?.data?.detail || 'Errore invio email.' })
    } finally {
      setTestingEmail(false)
    }
  }

  const handleTestLdap = async () => {
    setTestingLdap(true)
    setMessage(null)
    try {
      const res = await testLdap()
      setMessage({ type: 'ok', text: res.detail || 'Connessione riuscita.' })
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setMessage({ type: 'err', text: err?.response?.data?.detail || 'Errore connessione LDAP.' })
    } finally {
      setTestingLdap(false)
    }
  }

  if (loading || !data) {
    return (
      <div className="p-6">
        {loading ? <p className="text-slate-500">Caricamento...</p> : <p className="text-slate-500">Impostazioni non disponibili.</p>}
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl rounded-lg bg-white shadow">
      <div className="border-b border-slate-200 px-4 py-3">
        <Link to="/dashboard" className="text-sm text-indigo-600 hover:underline">← Dashboard</Link>
        <h1 className="mt-1 text-xl font-semibold text-slate-800">Impostazioni di sistema</h1>
      </div>
      <nav className="flex flex-wrap gap-2 border-b border-slate-200 px-4">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`border-b-2 px-3 py-2 text-sm font-medium ${
              tab === t.id ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-600 hover:text-slate-800'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>
      <div className="p-4">
        {message && (
          <p className={`mb-3 text-sm ${message.type === 'ok' ? 'text-green-600' : 'text-red-600'}`}>{message.text}</p>
        )}

        {tab === 'email' && (
          <div>
            <p className="mb-2 text-sm text-slate-600">Backend Console / SMTP. Configura l&apos;invio email.</p>
            <div className="mb-3 rounded border border-slate-200 p-3 text-sm text-slate-500">
              Configurazione in <code className="rounded bg-slate-100 px-1">settings</code> (variabili ambiente).
            </div>
            <button
              type="button"
              onClick={handleTestEmail}
              disabled={testingEmail}
              className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {testingEmail ? 'Invio...' : 'Invia email di test'}
            </button>
          </div>
        )}

        {tab === 'organization' && (
          <div>
            <p className="text-sm text-slate-600">Nome, codice, PEC, logo, formato protocollo.</p>
            <p className="mt-2 text-sm text-slate-500">Sezione in fase di configurazione.</p>
          </div>
        )}

        {tab === 'security' && (
          <div>
            <p className="text-sm text-slate-600">Tentativi login, timeout sessione, MFA per admin.</p>
            <p className="mt-2 text-sm text-slate-500">Sezione in fase di configurazione.</p>
          </div>
        )}

        {tab === 'storage' && (
          <div>
            <p className="text-sm text-slate-600">Dimensione massima upload (MB), estensioni permesse.</p>
            <p className="mt-2 text-sm text-slate-500">Sezione in fase di configurazione.</p>
          </div>
        )}

        {tab === 'ldap' && (
          <div>
            <p className="mb-2 text-sm text-slate-600">Abilita LDAP, server URI, bind DN, password, search base.</p>
            <div className="mb-3 rounded border border-slate-200 p-3 text-sm text-slate-500">
              Configurazione in <code className="rounded bg-slate-100 px-1">settings</code> o tramite impostazioni salvate.
            </div>
            <button
              type="button"
              onClick={handleTestLdap}
              disabled={testingLdap}
              className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {testingLdap ? 'Test...' : 'Testa connessione LDAP'}
            </button>
          </div>
        )}

        {tab === 'conservation' && (
          <div>
            <p className="text-sm text-slate-600">Provider (Mock / Aruba / Custom), API URL, API Key.</p>
            <p className="mt-2 text-sm text-slate-500">Sezione in fase di configurazione.</p>
          </div>
        )}
      </div>
    </div>
  )
}
