import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getSettings, patchSettings, testEmail, testLdap } from '../services/adminService'
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
  const [savingPolicy, setSavingPolicy] = useState(false)
  const [pwdDraft, setPwdDraft] = useState({
    password_min_length: 8,
    password_require_uppercase: true,
    password_require_lowercase: true,
    password_require_digit: true,
    password_require_special: true,
    password_expiry_days: 0,
    password_history_count: 0,
  })

  useEffect(() => {
    getSettings()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!data) return
    const s = data.security || {}
    setPwdDraft({
      password_min_length: Math.min(30, Math.max(6, Number(s.password_min_length ?? 8))),
      password_require_uppercase: s.password_require_uppercase !== false,
      password_require_lowercase: s.password_require_lowercase !== false,
      password_require_digit: s.password_require_digit !== false,
      password_require_special: s.password_require_special !== false,
      password_expiry_days: Math.max(0, Number(s.password_expiry_days ?? 0)),
      password_history_count: Math.max(0, Number(s.password_history_count ?? 0)),
    })
  }, [data])

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

  const handleSavePasswordPolicy = async () => {
    if (!data) return
    setSavingPolicy(true)
    setMessage(null)
    try {
      const updated = await patchSettings({
        security: {
          ...data.security,
          ...pwdDraft,
        },
      })
      setData(updated)
      setMessage({ type: 'ok', text: 'Policy password salvata.' })
    } catch {
      setMessage({ type: 'err', text: 'Salvataggio policy non riuscito.' })
    } finally {
      setSavingPolicy(false)
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
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Caricamento...</p>
        ) : (
          <p className="text-slate-500 dark:text-slate-400">Impostazioni non disponibili.</p>
        )}
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl rounded-lg border border-slate-200 bg-white shadow dark:border-slate-700 dark:bg-slate-800">
      <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
        <Link to="/dashboard" className="text-sm text-indigo-600 hover:underline dark:text-indigo-400">
          ← Dashboard
        </Link>
        <h1 className="mt-1 text-xl font-semibold text-slate-800 dark:text-slate-100">Impostazioni di sistema</h1>
      </div>
      <nav className="flex flex-wrap gap-2 border-b border-slate-200 px-4 dark:border-slate-700">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`border-b-2 px-3 py-2 text-sm font-medium ${
              tab === t.id
                ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                : 'border-transparent text-slate-600 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>
      <div className="p-4">
        {message && (
          <p
            className={`mb-3 text-sm ${
              message.type === 'ok' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
            }`}
          >
            {message.text}
          </p>
        )}

        {tab === 'email' && (
          <div>
            <p className="mb-2 text-sm text-slate-600 dark:text-slate-300">Backend Console / SMTP. Configura l&apos;invio email.</p>
            <div className="mb-3 rounded border border-slate-200 p-3 text-sm text-slate-500 dark:border-slate-600 dark:text-slate-400">
              Configurazione in{' '}
              <code className="rounded bg-slate-100 px-1 dark:bg-slate-700">settings</code> (variabili ambiente).
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
            <p className="text-sm text-slate-600 dark:text-slate-300">Nome, codice, PEC, logo, formato protocollo.</p>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Sezione in fase di configurazione.</p>
          </div>
        )}

        {tab === 'security' && (
          <div className="max-w-xl space-y-4">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Policy password applicata a creazione utenti, inviti e reset (validazione lato server).
            </p>
            <div>
              <label htmlFor="pwd-min-len" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Lunghezza minima (6–30)
              </label>
              <input
                id="pwd-min-len"
                type="number"
                min={6}
                max={30}
                value={pwdDraft.password_min_length}
                onChange={(e) =>
                  setPwdDraft((d) => ({ ...d, password_min_length: Number(e.target.value) || 6 }))
                }
                className="w-32 rounded border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
              />
            </div>
            <div className="flex flex-col gap-2 text-sm text-slate-800 dark:text-slate-200">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={pwdDraft.password_require_uppercase}
                  onChange={(e) => setPwdDraft((d) => ({ ...d, password_require_uppercase: e.target.checked }))}
                />
                Richiedi lettera maiuscola
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={pwdDraft.password_require_lowercase}
                  onChange={(e) => setPwdDraft((d) => ({ ...d, password_require_lowercase: e.target.checked }))}
                />
                Richiedi lettera minuscola
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={pwdDraft.password_require_digit}
                  onChange={(e) => setPwdDraft((d) => ({ ...d, password_require_digit: e.target.checked }))}
                />
                Richiedi numero
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={pwdDraft.password_require_special}
                  onChange={(e) => setPwdDraft((d) => ({ ...d, password_require_special: e.target.checked }))}
                />
                Richiedi carattere speciale
              </label>
            </div>
            <div>
              <label htmlFor="pwd-expiry" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Scadenza password (giorni, 0 = mai) — memorizzato in impostazioni; enforcement completo in evoluzione
              </label>
              <input
                id="pwd-expiry"
                type="number"
                min={0}
                value={pwdDraft.password_expiry_days}
                onChange={(e) =>
                  setPwdDraft((d) => ({ ...d, password_expiry_days: Math.max(0, Number(e.target.value) || 0) }))
                }
                className="w-32 rounded border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
              />
            </div>
            <div>
              <label htmlFor="pwd-history" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Storico password non riutilizzabili (0 = disabilitato)
              </label>
              <input
                id="pwd-history"
                type="number"
                min={0}
                value={pwdDraft.password_history_count}
                onChange={(e) =>
                  setPwdDraft((d) => ({ ...d, password_history_count: Math.max(0, Number(e.target.value) || 0) }))
                }
                className="w-32 rounded border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
              />
            </div>
            <button
              type="button"
              onClick={() => void handleSavePasswordPolicy()}
              disabled={savingPolicy}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 dark:hover:bg-indigo-500"
            >
              {savingPolicy ? 'Salvataggio...' : 'Salva policy password'}
            </button>
          </div>
        )}

        {tab === 'storage' && (
          <div>
            <p className="text-sm text-slate-600 dark:text-slate-300">Dimensione massima upload (MB), estensioni permesse.</p>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Sezione in fase di configurazione.</p>
          </div>
        )}

        {tab === 'ldap' && (
          <div>
            <p className="mb-2 text-sm text-slate-600 dark:text-slate-300">
              Abilita LDAP, server URI, bind DN, password, search base.
            </p>
            <div className="mb-3 rounded border border-slate-200 p-3 text-sm text-slate-500 dark:border-slate-600 dark:text-slate-400">
              Configurazione in{' '}
              <code className="rounded bg-slate-100 px-1 dark:bg-slate-700">settings</code> o tramite impostazioni salvate.
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
            <p className="text-sm text-slate-600 dark:text-slate-300">Provider (Mock / Aruba / Custom), API URL, API Key.</p>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Sezione in fase di configurazione.</p>
          </div>
        )}
      </div>
    </div>
  )
}
