import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  exportMyData,
  getMyConsents,
  grantConsent,
  type ConsentRecord,
  type ConsentType,
} from '../services/privacyService'
import { announce } from '../components/common/ScreenReaderAnnouncer'

const OPTIONAL: ConsentType[] = ['marketing', 'analytics', 'third_party']
const LABELS: Record<string, string> = {
  privacy_policy: 'Informativa privacy',
  data_processing: 'Trattamento dati',
  marketing: 'Comunicazioni marketing',
  analytics: 'Analisi e statistiche',
  third_party: 'Terze parti',
}

export function PrivacyConsentPage() {
  const [rows, setRows] = useState<ConsentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setRows(await getMyConsents())
    } catch {
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const latestByType = (t: string) =>
    rows.filter((r) => r.consent_type === t).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )[0]

  const revokeOptional = async (t: ConsentType) => {
    try {
      await grantConsent({ consent_type: t, granted: false, version: latestByType(t)?.version || '1.0' })
      announce(`Consenso ${LABELS[t] || t} revocato`)
      void load()
    } catch {
      announce('Errore durante l\'aggiornamento del consenso', 'assertive')
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      await exportMyData()
      announce('Esportazione dati personali avviata')
    } catch {
      announce('Esportazione non riuscita', 'assertive')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <Link to="/dashboard" className="text-sm text-indigo-600 hover:underline dark:text-indigo-400">
        ← Dashboard
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-slate-800 dark:text-slate-100">Privacy e consensi</h1>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
        Gestisci i consensi GDPR e scarica una copia dei tuoi dati (diritto alla portabilità).
      </p>

      <section className="mt-8 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Consensi registrati</h2>
        {loading ? (
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Caricamento…</p>
        ) : rows.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Nessun consenso registrato.</p>
        ) : (
          <ul className="mt-3 space-y-2 text-sm">
            {rows.map((r) => (
              <li
                key={r.id}
                className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 py-2 dark:border-slate-600"
              >
                <span className="text-slate-700 dark:text-slate-200">
                  {LABELS[r.consent_type] || r.consent_type} — v{r.version}
                </span>
                <span className={r.granted ? 'text-green-700 dark:text-green-400' : 'text-slate-500 dark:text-slate-400'}>
                  {r.granted ? 'Attivo' : 'Revocato'}
                </span>
                {OPTIONAL.includes(r.consent_type as ConsentType) && r.granted && (
                  <button
                    type="button"
                    onClick={() => void revokeOptional(r.consent_type as ConsentType)}
                    className="text-xs text-red-600 hover:underline dark:text-red-400"
                  >
                    Revoca
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
          I consensi obbligatori (privacy e trattamento dati) non possono essere revocati dall&apos;app: sono
          necessari per usare il servizio.
        </p>
      </section>

      <section className="mt-6 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Portabilità dati</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Scarica un file JSON con i dati personali associati al tuo account.
        </p>
        <button
          type="button"
          disabled={exporting}
          onClick={() => void handleExport()}
          className="mt-3 rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 dark:hover:bg-indigo-500"
        >
          {exporting ? 'Preparazione…' : 'Esporta i miei dati'}
        </button>
      </section>

      <section className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/30">
        <h2 className="text-lg font-semibold text-amber-900 dark:text-amber-100">Cancellazione account</h2>
        <p className="mt-2 text-sm text-amber-800 dark:text-amber-200">
          Per richiedere la cancellazione o l&apos;anonimizzazione dei dati (diritto all&apos;oblio), contatta
          l&apos;amministratore di sistema. Alcuni dati possono essere conservati per obblighi di legge.
        </p>
      </section>
    </div>
  )
}
