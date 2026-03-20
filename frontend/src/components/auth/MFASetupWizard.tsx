import { useState } from 'react'
import { Dialog, DialogTitle } from '@headlessui/react'
import { initMFASetup, confirmMFASetup } from '../../services/authService'

interface MFASetupWizardProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

const STEPS = ['instructions', 'scan', 'verify'] as const

export function MFASetupWizard({ open, onClose, onSuccess }: MFASetupWizardProps) {
  const [step, setStep] = useState(0)
  const [qrData, setQrData] = useState<{ secret: string; qr_code_base64: string; otpauth_uri: string } | null>(null)
  const [code, setCode] = useState('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const currentStep = STEPS[step]

  async function loadQr() {
    setError(null)
    setLoading(true)
    try {
      const data = await initMFASetup()
      setQrData(data)
      setStep(1)
    } catch {
      setError('Impossibile avviare il setup MFA')
    } finally {
      setLoading(false)
    }
  }

  function goToVerify() {
    setError(null)
    setCode('')
    setStep(2)
  }

  async function confirmCode() {
    if (!code || code.length !== 6) {
      setError('Inserisci il codice a 6 cifre')
      return
    }
    setError(null)
    setLoading(true)
    try {
      const res = await confirmMFASetup(code)
      setBackupCodes(res.backup_codes)
      setStep(3)
    } catch (err: unknown) {
      const res = (err as { response?: { data?: { code?: string; detail?: string } } })?.response
      setError(res?.data?.code ?? res?.data?.detail ?? 'Codice non valido')
    } finally {
      setLoading(false)
    }
  }

  function downloadBackupCodes() {
    const text = backupCodes.join('\n')
    const blob = new Blob([`Codici di recupero MFA AXDOC\n\n${text}\n\nSalva in un posto sicuro.`], {
      type: 'text/plain',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'axdoc-mfa-backup-codes.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  function finishWizard() {
    setStep(0)
    setQrData(null)
    setCode('')
    setBackupCodes([])
    setError(null)
    onSuccess()
    onClose()
  }

  if (!open) return null

  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="mx-auto max-h-[90vh] w-full max-w-md overflow-y-auto rounded-lg bg-white p-6 shadow-xl">
          <DialogTitle className="text-lg font-semibold text-slate-800">
            Configura autenticazione a due fattori
          </DialogTitle>

          {currentStep === 'instructions' && (
            <>
              <p className="mt-3 text-sm text-slate-600">
                Scarica un&apos;app authenticator (es. Google Authenticator o Authy) sul tuo dispositivo.
              </p>
              <div className="mt-4 flex gap-2">
                <a
                  href="https://apps.apple.com/app/google-authenticator/id388497605"
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-indigo-600 hover:underline"
                >
                  App Store
                </a>
                <a
                  href="https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2"
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-indigo-600 hover:underline"
                >
                  Google Play
                </a>
              </div>
              <div className="mt-6 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50"
                >
                  Annulla
                </button>
                <button
                  type="button"
                  onClick={loadQr}
                  disabled={loading}
                  className="rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {loading ? 'Caricamento...' : 'Continua'}
                </button>
              </div>
            </>
          )}

          {currentStep === 'scan' && qrData && (
            <>
              <p className="mt-3 text-sm text-slate-600">
                Scansiona questo QR code con la tua app authenticator.
              </p>
              <div className="mt-4 flex justify-center">
                <img
                  src={`data:image/png;base64,${qrData.qr_code_base64}`}
                  alt="QR Code MFA"
                  className="h-48 w-48"
                />
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Oppure inserisci manualmente: <code className="rounded bg-slate-100 px-1">{qrData.secret}</code>
              </p>
              <div className="mt-6 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setStep(0)}
                  className="rounded border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50"
                >
                  Indietro
                </button>
                <button
                  type="button"
                  onClick={goToVerify}
                  className="rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700"
                >
                  Continua
                </button>
              </div>
            </>
          )}

          {currentStep === 'verify' && (
            <>
              <p className="mt-3 text-sm text-slate-600">
                Inserisci il codice a 6 cifre mostrato dall&apos;app per confermare.
              </p>
              <div className="mt-4">
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="000000"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-center text-lg tracking-widest focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
              <div className="mt-6 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="rounded border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50"
                >
                  Indietro
                </button>
                <button
                  type="button"
                  onClick={confirmCode}
                  disabled={loading}
                  className="rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {loading ? 'Verifica...' : 'Attiva MFA'}
                </button>
              </div>
            </>
          )}

          {step === 3 && backupCodes.length > 0 && (
            <>
              <p className="mt-3 text-sm font-medium text-amber-800">
                Salva questi codici in un posto sicuro. Non potranno essere visualizzati di nuovo.
              </p>
              <ul className="mt-2 grid grid-cols-2 gap-1 rounded bg-slate-50 p-3 font-mono text-sm">
                {backupCodes.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
              <div className="mt-4 flex gap-2">
                <button
                  type="button"
                  onClick={downloadBackupCodes}
                  className="rounded border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50"
                >
                  Scarica codici
                </button>
                <button
                  type="button"
                  onClick={finishWizard}
                  className="rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700"
                >
                  Ho salvato i codici
                </button>
              </div>
            </>
          )}

          {error && currentStep !== 'verify' && (
            <div className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</div>
          )}
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
