import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { disableMFA } from '../services/authService'
import { MFASetupWizard } from '../components/auth/MFASetupWizard'
import { LDAPStatusCard } from '../components/auth/LDAPStatusCard'

export function ProfilePage() {
  const user = useAuthStore((s) => s.user)
  const [mfaWizardOpen, setMfaWizardOpen] = useState(false)
  const [mfaDisabled, setMfaDisabled] = useState(false)
  const [disableCode, setDisableCode] = useState('')
  const [disableError, setDisableError] = useState<string | null>(null)
  const mfaEnabled = user?.mfa_enabled ?? false

  async function handleDisableMFA() {
    if (!disableCode || disableCode.length !== 6) {
      setDisableError('Inserisci il codice a 6 cifre')
      return
    }
    setDisableError(null)
    try {
      await disableMFA({ code: disableCode })
      setMfaDisabled(false)
      setDisableCode('')
      useAuthStore.getState().initializeAuth()
    } catch {
      setDisableError('Codice non valido')
    }
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Profilo</h1>
      {user && (
        <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <p className="text-slate-700 dark:text-slate-200">
            <span className="font-medium">Nome:</span> {user.first_name} {user.last_name}
          </p>
          <p className="text-slate-700 dark:text-slate-200">
            <span className="font-medium">Email:</span> {user.email}
          </p>
          <p className="text-slate-700 dark:text-slate-200">
            <span className="font-medium">Ruolo:</span> {user.role}
          </p>
        </div>
      )}

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Privacy e GDPR</h2>
        <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Consensi, esportazione dati e informazioni sul trattamento.
          </p>
          <Link
            to="/privacy"
            className="mt-2 inline-block rounded bg-slate-200 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-300 dark:bg-slate-600 dark:text-slate-100 dark:hover:bg-slate-500"
          >
            Apri privacy e consensi
          </Link>
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Cambio password</h2>
        <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <p className="text-sm text-slate-600 dark:text-slate-300">Modifica la password del tuo account.</p>
          <Link
            to="/change-password"
            className="mt-2 inline-block rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
          >
            Cambia password
          </Link>
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-slate-800">Sicurezza</h2>
        <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-800">Autenticazione a due fattori (MFA)</p>
              <p className="text-sm text-slate-600">
                Aggiungi un livello di sicurezza in più con un codice dall&apos;app authenticator.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {mfaEnabled ? (
                <>
                  <span className="rounded bg-green-100 px-2 py-1 text-sm text-green-800">MFA Attivo ✓</span>
                  <button
                    type="button"
                    onClick={() => setMfaDisabled(true)}
                    className="rounded border border-red-300 px-3 py-1 text-sm text-red-700 hover:bg-red-50"
                  >
                    Disabilita
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => setMfaWizardOpen(true)}
                  className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
                >
                  Abilita MFA
                </button>
              )}
            </div>
          </div>
        </div>

        {mfaDisabled && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm text-amber-800">Inserisci il codice TOTP per disabilitare MFA.</p>
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              placeholder="000000"
              value={disableCode}
              onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, ''))}
              className="mt-2 w-32 rounded border border-slate-300 px-3 py-2 text-center focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            {disableError && <p className="mt-1 text-sm text-red-600">{disableError}</p>}
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => { setMfaDisabled(false); setDisableCode(''); setDisableError(null); }}
                className="rounded border border-slate-300 px-3 py-1 text-slate-700 hover:bg-slate-50"
              >
                Annulla
              </button>
              <button
                type="button"
                onClick={handleDisableMFA}
                className="rounded bg-red-600 px-3 py-1 text-white hover:bg-red-700"
              >
                Disabilita MFA
              </button>
            </div>
          </div>
        )}
      </section>

      {user?.role === 'ADMIN' && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold text-slate-800">Impostazioni sistema</h2>
          <LDAPStatusCard />
        </section>
      )}

      <MFASetupWizard
        open={mfaWizardOpen}
        onClose={() => setMfaWizardOpen(false)}
        onSuccess={() => {
          useAuthStore.getState().initializeAuth()
        }}
      />
    </div>
  )
}
