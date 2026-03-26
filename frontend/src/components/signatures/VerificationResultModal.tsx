import type { ReactNode } from 'react'
import { useCallback } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useModalEscape } from '../../hooks/useModalAccessibility'

interface VerificationResultModalProps {
  result: Record<string, unknown>
  onClose: () => void
}

export function VerificationResultModal({ result, onClose }: VerificationResultModalProps) {
  const modalRef = useFocusTrap(true)
  const closeCb = useCallback(() => onClose(), [onClose])
  useModalEscape(true, closeCb)

  const valid = result.valid === true
  const error = result.error as string | undefined
  const signerCn = (result.signer_cn as string) ?? ''
  const signerEmail = (result.signer_email as string) ?? ''
  const certificateIssuer = (result.certificate_issuer as string) ?? ''
  const validFrom = result.certificate_valid_from as string | undefined
  const validTo = result.certificate_valid_to as string | undefined
  const signedAt = result.signed_at as string | undefined
  const timestampToken = result.timestamp_token as string | undefined
  const revocationStatus = (result.revocation_status as string) ?? ''
  const errors = (result.errors as string[] | undefined) ?? []

  let statusLabel: ReactNode
  let statusClass: string
  if (error) {
    statusLabel = '❌ Non valida'
    statusClass = 'text-red-700 bg-red-50'
  } else if (valid) {
    statusLabel = '✅ Valida'
    statusClass = 'text-green-700 bg-green-50'
  } else {
    statusLabel = '⚠️ Scaduta / Non valida'
    statusClass = 'text-amber-700 bg-amber-50'
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title-verification-result"
        className="w-full max-w-lg rounded-lg bg-white shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 id="modal-title-verification-result" className="text-lg font-semibold text-slate-800">
            Risultato verifica firma
          </h2>
          <button type="button" onClick={onClose} className="rounded p-1 text-slate-500 hover:bg-slate-100">
            ✕
          </button>
        </div>
        <div className="p-4 space-y-3">
          <div className={`rounded px-3 py-2 font-medium ${statusClass}`}>
            {statusLabel}
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          {signerCn && <p className="text-sm"><span className="font-medium text-slate-500">Firmatario (CN):</span> {signerCn}</p>}
          {signerEmail && <p className="text-sm"><span className="font-medium text-slate-500">Email:</span> {signerEmail}</p>}
          {certificateIssuer && <p className="text-sm"><span className="font-medium text-slate-500">Emittente certificato:</span> {certificateIssuer}</p>}
          {(validFrom || validTo) && (
            <p className="text-sm">
              <span className="font-medium text-slate-500">Validità certificato:</span>{' '}
              {validFrom ? new Date(validFrom).toLocaleDateString() : '—'} – {validTo ? new Date(validTo).toLocaleDateString() : '—'}
            </p>
          )}
          {signedAt && <p className="text-sm"><span className="font-medium text-slate-500">Data firma:</span> {new Date(signedAt).toLocaleString()}</p>}
          {timestampToken && <p className="text-sm"><span className="font-medium text-slate-500">Marca temporale:</span> presente</p>}
          {revocationStatus && <p className="text-sm"><span className="font-medium text-slate-500">Stato revoca:</span> {revocationStatus}</p>}
          {errors.length > 0 && (
            <ul className="text-sm text-red-600 list-disc list-inside">
              {errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </div>
        <div className="border-t border-slate-200 px-4 py-3">
          <button type="button" onClick={onClose} className="rounded bg-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-300">
            Chiudi
          </button>
        </div>
      </div>
    </div>
  )
}
