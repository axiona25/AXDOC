import { useState } from 'react'
import { verifyP7M, extractP7MContent, type P7MVerifyResult, type P7MSignerInfo } from '../../services/signatureService'

interface P7MViewerProps {
  file?: File
  url?: string
  fileName?: string
  onDownload?: () => void
}

async function formatApiError(e: unknown, fallback: string): Promise<string> {
  const err = e as { response?: { data?: unknown } }
  const d = err?.response?.data
  if (d instanceof Blob) {
    try {
      const t = await d.text()
      const j = JSON.parse(t) as { detail?: string }
      return j.detail || t || fallback
    } catch {
      return fallback
    }
  }
  if (d && typeof d === 'object' && 'detail' in d && typeof (d as { detail: unknown }).detail === 'string') {
    return (d as { detail: string }).detail
  }
  return fallback
}

export function P7MViewer({ file, url, fileName, onDownload }: P7MViewerProps) {
  const [verifyResult, setVerifyResult] = useState<P7MVerifyResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [error, setError] = useState('')

  const handleVerify = async () => {
    let fileToVerify = file
    if (!fileToVerify && url) {
      try {
        const resp = await fetch(url)
        const blob = await resp.blob()
        fileToVerify = new File([blob], fileName || 'document.p7m')
      } catch {
        setError('Impossibile scaricare il file per la verifica.')
        return
      }
    }
    if (!fileToVerify) {
      setError('Nessun file da verificare.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const result = await verifyP7M(fileToVerify)
      setVerifyResult(result)
    } catch (e: unknown) {
      setError(await formatApiError(e, 'Errore verifica.'))
    } finally {
      setLoading(false)
    }
  }

  const handleExtract = async () => {
    let fileToExtract = file
    if (!fileToExtract && url) {
      try {
        const resp = await fetch(url)
        const blob = await resp.blob()
        fileToExtract = new File([blob], fileName || 'document.p7m')
      } catch {
        setError('Impossibile scaricare il file.')
        return
      }
    }
    if (!fileToExtract) return

    setExtracting(true)
    try {
      const blob = await extractP7MContent(fileToExtract)
      const originalName = (fileName || 'document.p7m').replace(/\.p7m$/i, '')
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = originalName
      a.click()
      URL.revokeObjectURL(a.href)
    } catch (e: unknown) {
      setError(await formatApiError(e, 'Errore estrazione.'))
    } finally {
      setExtracting(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between gap-2 border-b border-slate-200 px-3 py-2 bg-slate-50">
        <div className="flex items-center gap-2">
          <span className="text-lg">🔏</span>
          <span className="text-sm font-medium text-slate-800">{fileName || 'File P7M'}</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleVerify}
            disabled={loading}
            className="rounded bg-indigo-600 px-3 py-1 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? 'Verifica...' : '🔍 Verifica firma'}
          </button>
          <button
            type="button"
            onClick={handleExtract}
            disabled={extracting}
            className="rounded bg-slate-200 px-3 py-1 text-sm text-slate-700 hover:bg-slate-300 disabled:opacity-50"
          >
            {extracting ? 'Estrazione...' : '📄 Estrai documento'}
          </button>
          {onDownload && (
            <button
              type="button"
              onClick={onDownload}
              className="rounded bg-slate-200 px-3 py-1 text-sm text-slate-700 hover:bg-slate-300"
            >
              Scarica P7M
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {error && (
          <div className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
        )}

        {!verifyResult && !loading && (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <span className="text-5xl mb-4">🔏</span>
            <p className="text-lg font-medium">File con firma digitale CAdES (.p7m)</p>
            <p className="text-sm mt-1">Clicca &quot;Verifica firma&quot; per controllare la validità della firma digitale</p>
            <p className="text-sm">oppure &quot;Estrai documento&quot; per scaricare il file originale</p>
          </div>
        )}

        {verifyResult && (
          <div className="space-y-4">
            <div
              className={`rounded-lg border p-4 ${verifyResult.valid ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50'}`}
            >
              <div className="flex items-center gap-2">
                <span className="text-2xl">{verifyResult.valid ? '✅' : '❌'}</span>
                <div>
                  <p className={`font-semibold ${verifyResult.valid ? 'text-green-800' : 'text-red-800'}`}>
                    {verifyResult.valid ? 'Firma valida' : 'Firma non valida'}
                  </p>
                  <p className="text-sm text-slate-600">{verifyResult.signers.length} firmatario/i trovato/i</p>
                </div>
              </div>
            </div>

            {verifyResult.signers.map((signer, i) => (
              <SignerCard key={i} signer={signer} index={i} />
            ))}

            {verifyResult.errors.length > 0 && (
              <div className="rounded border border-amber-200 bg-amber-50 p-3">
                <p className="text-sm font-medium text-amber-800 mb-1">Avvisi</p>
                {verifyResult.errors.map((err, i) => (
                  <p key={i} className="text-xs text-amber-700">
                    {err}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function SignerCard({ signer, index }: { signer: P7MSignerInfo; index: number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-slate-800">Firmatario {index + 1}</h4>
        {signer.is_expired ? (
          <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">Certificato scaduto</span>
        ) : (
          <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">Certificato valido</span>
        )}
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <div>
          <dt className="text-slate-500">Nome</dt>
          <dd className="font-medium text-slate-800">{signer.common_name || '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Email</dt>
          <dd className="text-slate-800">{signer.email || '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Organizzazione</dt>
          <dd className="text-slate-800">{signer.organization || '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Codice fiscale / Seriale</dt>
          <dd className="text-slate-800 font-mono text-xs">{signer.serial_number || '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Ente certificatore</dt>
          <dd className="text-slate-800">{signer.issuer || '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Validità</dt>
          <dd className="text-slate-800">
            {signer.valid_from ? new Date(signer.valid_from).toLocaleDateString('it-IT') : '?'}
            {' — '}
            {signer.valid_to ? new Date(signer.valid_to).toLocaleDateString('it-IT') : '?'}
          </dd>
        </div>
      </dl>
    </div>
  )
}
