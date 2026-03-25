import { useCallback, useEffect, useState } from 'react'
import { useAuthStore } from '../../store/authStore'
import { getMyConsents, grantConsent, type ConsentType } from '../../services/privacyService'

/** Versione informativa: allineare al default backend `gdpr_privacy_policy_version`. */
export const PRIVACY_POLICY_VERSION = '1.0'

const REQUIRED_TYPES: ConsentType[] = ['privacy_policy', 'data_processing']

function needsBanner(consents: { consent_type: string; version: string; granted: boolean }[]): boolean {
  for (const t of REQUIRED_TYPES) {
    const row = consents.find((c) => c.consent_type === t && c.granted)
    if (!row || row.version !== PRIVACY_POLICY_VERSION) return true
  }
  return false
}

export function PrivacyBanner() {
  const user = useAuthStore((s) => s.user)
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [privacyOk, setPrivacyOk] = useState(false)
  const [dataOk, setDataOk] = useState(false)
  const [marketing, setMarketing] = useState(false)
  const [analytics, setAnalytics] = useState(false)

  const check = useCallback(async () => {
    if (!user) {
      setLoading(false)
      return
    }
    try {
      const list = await getMyConsents()
      setOpen(needsBanner(list))
    } catch {
      setOpen(true)
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    setLoading(true)
    void check()
  }, [check])

  const handleAccept = async () => {
    if (!privacyOk || !dataOk) return
    setSubmitting(true)
    try {
      await grantConsent({
        consent_type: 'privacy_policy',
        granted: true,
        version: PRIVACY_POLICY_VERSION,
      })
      await grantConsent({
        consent_type: 'data_processing',
        granted: true,
        version: PRIVACY_POLICY_VERSION,
      })
      await grantConsent({
        consent_type: 'marketing',
        granted: marketing,
        version: PRIVACY_POLICY_VERSION,
      })
      await grantConsent({
        consent_type: 'analytics',
        granted: analytics,
        version: PRIVACY_POLICY_VERSION,
      })
      setOpen(false)
    } catch {
      /* toast opzionale */
    } finally {
      setSubmitting(false)
    }
  }

  if (!user || loading || !open) return null

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="privacy-banner-title"
      aria-describedby="privacy-banner-desc"
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-600 dark:bg-slate-800">
        <h2 id="privacy-banner-title" className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          Informativa privacy e consensi
        </h2>
        <p id="privacy-banner-desc" className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Per continuare è necessario accettare l&apos;informativa sulla privacy e il trattamento dei dati
          personali (GDPR). Le opzioni di marketing e analisi sono facoltative.
        </p>
        <ul className="mt-4 space-y-3 text-sm">
          <li className="flex gap-2">
            <input
              id="pb-privacy"
              type="checkbox"
              checked={privacyOk}
              onChange={(e) => setPrivacyOk(e.target.checked)}
              className="mt-1"
            />
            <label htmlFor="pb-privacy" className="text-slate-700 dark:text-slate-200">
              Accetto l&apos;informativa privacy (obbligatorio)
            </label>
          </li>
          <li className="flex gap-2">
            <input
              id="pb-data"
              type="checkbox"
              checked={dataOk}
              onChange={(e) => setDataOk(e.target.checked)}
              className="mt-1"
            />
            <label htmlFor="pb-data" className="text-slate-700 dark:text-slate-200">
              Acconsento al trattamento dei dati personali per l&apos;erogazione del servizio (obbligatorio)
            </label>
          </li>
          <li className="flex gap-2">
            <input
              id="pb-mkt"
              type="checkbox"
              checked={marketing}
              onChange={(e) => setMarketing(e.target.checked)}
              className="mt-1"
            />
            <label htmlFor="pb-mkt" className="text-slate-600 dark:text-slate-300">
              Acconsento a comunicazioni commerciali (facoltativo)
            </label>
          </li>
          <li className="flex gap-2">
            <input
              id="pb-an"
              type="checkbox"
              checked={analytics}
              onChange={(e) => setAnalytics(e.target.checked)}
              className="mt-1"
            />
            <label htmlFor="pb-an" className="text-slate-600 dark:text-slate-300">
              Acconsento a statistiche e analisi aggregate (facoltativo)
            </label>
          </li>
        </ul>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            disabled={!privacyOk || !dataOk || submitting}
            onClick={() => void handleAccept()}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 dark:hover:bg-indigo-500"
          >
            {submitting ? 'Salvataggio…' : 'Accetta e continua'}
          </button>
        </div>
      </div>
    </div>
  )
}
