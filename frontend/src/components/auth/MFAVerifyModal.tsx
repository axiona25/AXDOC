import { useState, useRef, useEffect, useId, useCallback } from 'react'
import { Dialog, DialogTitle } from '@headlessui/react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useModalEscape } from '../../hooks/useModalAccessibility'
import { verifyMFA } from '../../services/authService'
import type { User } from '../../types/auth'

interface MFAVerifyModalProps {
  open: boolean
  mfaPendingToken: string
  onSuccess: (user: User) => void
  onClose?: () => void
}

export function MFAVerifyModal({ open, mfaPendingToken, onSuccess, onClose }: MFAVerifyModalProps) {
  const titleId = useId()
  const trapRef = useFocusTrap(open)
  const [code, setCode] = useState('')
  const [backupCode, setBackupCode] = useState('')
  const [useBackup, setUseBackup] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const submittedRef = useRef(false)

  useEffect(() => {
    if (open) {
      setCode('')
      setBackupCode('')
      setError(null)
      setUseBackup(false)
      submittedRef.current = false
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open])

  useEffect(() => {
    if (code.length < 6) submittedRef.current = false
    if (!open || useBackup || code.length !== 6 || submittedRef.current) return
    submittedRef.current = true
    submitCode()
  }, [open, useBackup, code])

  async function submitCode() {
    if (!mfaPendingToken) return
    setError(null)
    setLoading(true)
    try {
      const payload = useBackup
        ? { backup_code: backupCode.trim() }
        : { code: code.trim() }
      if (useBackup && !backupCode.trim()) {
        setError('Inserisci il codice di recupero')
        setLoading(false)
        return
      }
      if (!useBackup && code.length !== 6) {
        setError('Codice a 6 cifre richiesto')
        setLoading(false)
        return
      }
      const res = await verifyMFA(mfaPendingToken, payload)
      onSuccess(res.user)
    } catch (err: unknown) {
      const res = (err as { response?: { data?: { detail?: string } } })?.response
      setError(res?.data?.detail ?? 'Codice non valido.')
    } finally {
      setLoading(false)
    }
  }

  const handleBackupSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    submitCode()
  }

  const closeModal = useCallback(() => {
    onClose?.()
  }, [onClose])
  useModalEscape(open, closeModal)

  return (
    <Dialog open={open} onClose={onClose ?? (() => {})} className="relative z-50">
      <div
        className="fixed inset-0 bg-black/30"
        aria-hidden="true"
        role="presentation"
        onMouseDown={(e) => {
          if (e.target === e.currentTarget) closeModal()
        }}
      />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel
          ref={trapRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          className="mx-auto w-full max-w-sm rounded-lg bg-white p-6 shadow-xl"
        >
          <DialogTitle id={titleId} className="text-lg font-semibold text-slate-800">
            Verifica in due passaggi
          </DialogTitle>
          <p className="mt-1 text-sm text-slate-600">
            Inserisci il codice a 6 cifre dall&apos;app authenticator.
          </p>

          {!useBackup ? (
            <>
              <div className="mt-4">
                <input
                  ref={inputRef}
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="000000"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-center text-lg tracking-widest focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <p className="mt-2 text-xs text-slate-500">Il codice cambia ogni 30 secondi.</p>
            </>
          ) : (
            <form onSubmit={handleBackupSubmit} className="mt-4">
              <input
                type="text"
                placeholder="Codice di recupero"
                value={backupCode}
                onChange={(e) => setBackupCode(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <button
                type="submit"
                disabled={loading}
                className="mt-3 w-full rounded bg-indigo-600 py-2 text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading ? 'Verifica...' : 'Usa codice di recupero'}
              </button>
            </form>
          )}

          {error && (
            <div className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</div>
          )}

          {!useBackup && (
            <button
              type="button"
              onClick={() => setUseBackup(true)}
              className="mt-4 w-full text-sm text-indigo-600 hover:underline"
            >
              Usa codice di recupero
            </button>
          )}
          {useBackup && (
            <button
              type="button"
              onClick={() => setUseBackup(false)}
              className="mt-2 w-full text-sm text-slate-500 hover:underline"
            >
              Torna al codice app
            </button>
          )}
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
