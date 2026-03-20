import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getPublicShare, verifySharePassword, downloadSharedFile } from '../services/sharingService'
import type { PublicShareData } from '../services/sharingService'

type PageState = 'loading' | 'password' | 'valid' | 'expired' | 'not_found'

export function PublicSharePage() {
  const { token } = useParams<{ token: string }>()
  const [state, setState] = useState<PageState>('loading')
  const [data, setData] = useState<PublicShareData | null>(null)
  const [password, setPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [verifiedPassword, setVerifiedPassword] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    if (!token) {
      setState('not_found')
      return
    }
    getPublicShare(token)
      .then((d) => {
        setData(d)
        setState('valid')
      })
      .catch((err: { response?: { status: number; data?: { requires_password?: boolean; detail?: string } } }) => {
        const status = err?.response?.status
        const resData = err?.response?.data
        if (status === 401 && resData?.requires_password) {
          setState('password')
          return
        }
        if (status === 410) {
          setState('expired')
          return
        }
        if (status === 404) {
          setState('not_found')
          return
        }
        setState('expired')
      })
  }, [token])

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    setPasswordError('')
    verifySharePassword(token, password)
      .then((res) => {
        if (res.valid && res.data) {
          setData(res.data)
          setVerifiedPassword(password)
          setState('valid')
        } else {
          setPasswordError('Password non corretta.')
        }
      })
      .catch(() => setPasswordError('Password non corretta.'))
  }

  const handleDownload = async () => {
    if (!token || !data?.can_download) return
    setDownloading(true)
    try {
      const blob = await downloadSharedFile(token, verifiedPassword ?? undefined)
      const doc = data.document
      const name = doc?.title ? `${doc.title}.pdf` : 'document.pdf'
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = name
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setPasswordError('Impossibile scaricare il file.')
    } finally {
      setDownloading(false)
    }
  }

  const formatDate = (s: string | null) => {
    if (!s) return null
    try {
      return new Date(s).toLocaleString('it-IT', { dateStyle: 'long', timeStyle: 'short' })
    } catch {
      return s
    }
  }

  if (!token) return null

  return (
    <div className="min-h-screen bg-slate-100 py-8 px-4">
      <div className="mx-auto max-w-2xl">
        {state === 'loading' && (
          <div className="rounded-lg bg-white p-8 text-center shadow">
            <p className="text-slate-600">Caricamento...</p>
          </div>
        )}

        {state === 'password' && (
          <div className="rounded-lg bg-white p-6 shadow">
            <h1 className="text-lg font-semibold text-slate-800">Accesso protetto da password</h1>
            <p className="mt-2 text-sm text-slate-600">Inserisci la password per accedere al documento condiviso.</p>
            <form onSubmit={handlePasswordSubmit} className="mt-4 space-y-3">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                autoFocus
              />
              {passwordError && <p className="text-sm text-red-600">{passwordError}</p>}
              <button
                type="submit"
                className="w-full rounded bg-indigo-600 px-3 py-2 text-sm text-white hover:bg-indigo-700"
              >
                Accedi
              </button>
            </form>
          </div>
        )}

        {state === 'valid' && data && (
          <div className="rounded-lg bg-white p-6 shadow">
            <p className="text-sm text-slate-500">
              Documento condiviso da <strong className="text-slate-700">{data.shared_by.name || data.shared_by.email}</strong>
            </p>
            <div className="mt-4 rounded border border-slate-200 bg-slate-50/50 p-4">
              {data.document && (
                <>
                  <h2 className="text-lg font-semibold text-slate-800">{data.document.title}</h2>
                  {data.document.description && (
                    <p className="mt-2 text-sm text-slate-600">{data.document.description}</p>
                  )}
                  <p className="mt-1 text-xs text-slate-500">
                    Versione {data.document.current_version} · Stato: {data.document.status}
                  </p>
                </>
              )}
            </div>
            {data.expires_at && (
              <p className="mt-3 text-xs text-slate-500">
                Scadenza link: {formatDate(data.expires_at)}
              </p>
            )}
            {data.can_download && (
              <button
                type="button"
                disabled={downloading}
                onClick={handleDownload}
                className="mt-4 rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {downloading ? 'Download in corso...' : 'Scarica documento'}
              </button>
            )}
            <p className="mt-4 text-xs text-slate-500">
              Accesso in sola lettura. Effettua il login per ulteriori azioni.
            </p>
            <Link to="/login" className="mt-2 inline-block text-sm text-indigo-600 hover:underline">
              Vai al login
            </Link>
          </div>
        )}

        {state === 'expired' && (
          <div className="rounded-lg bg-white p-8 text-center shadow">
            <h1 className="text-lg font-semibold text-slate-800">Questo link non è più valido.</h1>
            <p className="mt-2 text-sm text-slate-600">La condivisione è scaduta o è stata revocata.</p>
            <Link
              to="/login"
              className="mt-4 inline-block rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
            >
              Vai al login
            </Link>
          </div>
        )}

        {state === 'not_found' && (
          <div className="rounded-lg bg-white p-8 text-center shadow">
            <h1 className="text-lg font-semibold text-slate-800">Link non trovato</h1>
            <p className="mt-2 text-sm text-slate-600">Il link di condivisione non esiste o non è più disponibile.</p>
            <Link
              to="/login"
              className="mt-4 inline-block rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
            >
              Vai al login
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
