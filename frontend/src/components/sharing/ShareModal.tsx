import { useState, useEffect } from 'react'
import type { CreateSharePayload, CreateShareResponse } from '../../services/sharingService'
import { getUsers } from '../../services/userService'
import type { User } from '../../types/auth'

interface ShareModalProps {
  open: boolean
  onClose: () => void
  onSuccess: (res: CreateShareResponse) => void
  shareDocument?: (docId: string, data: CreateSharePayload) => Promise<CreateShareResponse>
  shareProtocol?: (protoId: string, data: CreateSharePayload) => Promise<CreateShareResponse>
  targetId: string
  targetLabel: string
}

const EXPIRY_OPTIONS: { value: number | null; label: string }[] = [
  { value: null, label: 'Nessuna' },
  { value: 1, label: '1 giorno' },
  { value: 7, label: '7 giorni' },
  { value: 30, label: '30 giorni' },
]

export function ShareModal({
  open,
  onClose,
  onSuccess,
  shareDocument,
  shareProtocol,
  targetId,
  targetLabel,
}: ShareModalProps) {
  const [recipientType, setRecipientType] = useState<'internal' | 'external'>('external')
  const [recipientUserId, setRecipientUserId] = useState('')
  const [recipientEmail, setRecipientEmail] = useState('')
  const [recipientName, setRecipientName] = useState('')
  const [canDownload, setCanDownload] = useState(true)
  const [expiresInDays, setExpiresInDays] = useState<number | null>(7)
  const [passwordProtected, setPasswordProtected] = useState(false)
  const [password, setPassword] = useState('')
  const [userSearch, setUserSearch] = useState('')
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<CreateShareResponse | null>(null)
  const [copied, setCopied] = useState(false)

  const doShare = async () => {
    setError('')
    const payload: CreateSharePayload = {
      recipient_type: recipientType,
      can_download: canDownload,
      expires_in_days: expiresInDays,
    }
    if (recipientType === 'internal') {
      if (!recipientUserId) {
        setError('Seleziona un utente.')
        return
      }
      payload.recipient_user_id = recipientUserId
    } else {
      if (!recipientEmail.trim()) {
        setError('Inserisci l\'email del destinatario.')
        return
      }
      payload.recipient_email = recipientEmail.trim()
      if (recipientName.trim()) payload.recipient_name = recipientName.trim()
    }
    if (passwordProtected && password.trim()) payload.password = password.trim()

    setLoading(true)
    try {
      const res = shareDocument
        ? await shareDocument(targetId, payload)
        : shareProtocol
          ? await shareProtocol(targetId, payload)
          : (() => { throw new Error('Nessuna azione di condivisione') })()
      setResult(res)
      onSuccess(res)
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { detail?: string } } })?.response?.data
      setError(data?.detail || 'Errore durante la condivisione.')
    } finally {
      setLoading(false)
    }
  }

  const handleCopyLink = () => {
    if (!result?.url) return
    navigator.clipboard.writeText(result.url).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const resetAndClose = () => {
    setResult(null)
    setRecipientType('external')
    setRecipientUserId('')
    setRecipientEmail('')
    setRecipientName('')
    setExpiresInDays(7)
    setPasswordProtected(false)
    setPassword('')
    setError('')
    onClose()
  }

  useEffect(() => {
    if (open && recipientType === 'internal') {
      getUsers({ search: userSearch || undefined }).then((r) => setUsers(r.results || []))
    }
  }, [open, recipientType, userSearch])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={resetAndClose}>
      <div className="max-h-[90vh] w-full max-w-md overflow-auto rounded-lg bg-white p-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <h3 className="text-lg font-semibold text-slate-800">Condividi {targetLabel}</h3>
          <button type="button" onClick={resetAndClose} className="rounded p-1 text-slate-500 hover:bg-slate-100">✕</button>
        </div>

        {result ? (
          <div className="space-y-3 pt-3">
            <p className="text-sm text-slate-600">Link creato. Condividi questo link con il destinatario:</p>
            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={result.url}
                className="flex-1 rounded border border-slate-200 bg-slate-50 px-2 py-1.5 text-sm"
              />
              <button
                type="button"
                onClick={handleCopyLink}
                className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700"
              >
                {copied ? 'Copiato!' : 'Copia link'}
              </button>
            </div>
            <button type="button" onClick={resetAndClose} className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-300">
              Chiudi
            </button>
          </div>
        ) : (
          <>
            <div className="space-y-3 pt-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">Destinatario</label>
                <div className="mt-1 flex gap-2">
                  <button
                    type="button"
                    onClick={() => setRecipientType('internal')}
                    className={`rounded px-3 py-1.5 text-sm ${recipientType === 'internal' ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700'}`}
                  >
                    Utente interno
                  </button>
                  <button
                    type="button"
                    onClick={() => setRecipientType('external')}
                    className={`rounded px-3 py-1.5 text-sm ${recipientType === 'external' ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700'}`}
                  >
                    Utente esterno
                  </button>
                </div>
              </div>

              {recipientType === 'internal' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700">Utente</label>
                  <div className="mt-1 flex gap-2">
                    <input
                      type="text"
                      placeholder="Cerca per email..."
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      className="flex-1 rounded border border-slate-200 px-2 py-1.5 text-sm"
                    />
                  </div>
                  <select
                    value={recipientUserId}
                    onChange={(e) => setRecipientUserId(e.target.value)}
                    className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                  >
                    <option value="">Seleziona utente</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>{u.email}</option>
                    ))}
                  </select>
                </div>
              )}

              {recipientType === 'external' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Email *</label>
                    <input
                      type="email"
                      value={recipientEmail}
                      onChange={(e) => setRecipientEmail(e.target.value)}
                      className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                      placeholder="email@esempio.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Nome (opzionale)</label>
                    <input
                      type="text"
                      value={recipientName}
                      onChange={(e) => setRecipientName(e.target.value)}
                      className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                      placeholder="Mario Rossi"
                    />
                  </div>
                </>
              )}

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="can_download"
                  checked={canDownload}
                  onChange={(e) => setCanDownload(e.target.checked)}
                />
                <label htmlFor="can_download" className="text-sm text-slate-700">Permetti download</label>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">Scadenza</label>
                <select
                  value={expiresInDays ?? ''}
                  onChange={(e) => setExpiresInDays(e.target.value === '' ? null : Number(e.target.value))}
                  className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                >
                  {EXPIRY_OPTIONS.map((o) => (
                    <option key={o.value ?? 'none'} value={o.value ?? ''}>{o.label}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="pwd"
                  checked={passwordProtected}
                  onChange={(e) => setPasswordProtected(e.target.checked)}
                />
                <label htmlFor="pwd" className="text-sm text-slate-700">Proteggi con password</label>
              </div>
              {passwordProtected && (
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  className="w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                />
              )}

              {error && <p className="text-sm text-red-600">{error}</p>}
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={resetAndClose} className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-300">
                Annulla
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={doShare}
                className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading ? 'Condivisione...' : 'Condividi'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
