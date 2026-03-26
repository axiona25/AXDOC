import { useState, useCallback } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useModalEscape } from '../../hooks/useModalAccessibility'
import type { SignatureRequestItem } from '../../types/signatures'

interface SignNowModalProps {
  signatureRequest: SignatureRequestItem
  onClose: () => void
  onSign: (simulate: boolean) => void
}

export function SignNowModal({ signatureRequest, onClose, onSign }: SignNowModalProps) {
  const [simulate, setSimulate] = useState(true)
  const [loading, setLoading] = useState(false)
  const modalRef = useFocusTrap(true)
  const closeCb = useCallback(() => onClose(), [onClose])
  useModalEscape(true, closeCb)

  const handleSign = () => {
    setLoading(true)
    onSign(simulate)
    setLoading(false)
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
        aria-labelledby="modal-title-sign-now"
        className="w-full max-w-md rounded-lg bg-white shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 id="modal-title-sign-now" className="text-lg font-semibold text-slate-800">
            Firma documento
          </h2>
          <button type="button" onClick={onClose} className="rounded p-1 text-slate-500 hover:bg-slate-100">
            ✕
          </button>
        </div>
        <div className="p-4 space-y-4">
          <p className="text-sm text-slate-600">
            Tipo firma: <strong>{signatureRequest.format === 'cades' ? 'CAdES' : signatureRequest.format}</strong>
          </p>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={simulate} onChange={(e) => setSimulate(e.target.checked)} />
            <span className="text-sm text-slate-700">Simula firma con certificato mock (ambiente di sviluppo)</span>
          </label>
          <p className="text-xs text-slate-500">
            In produzione: inserire PIN e caricare certificato .p12/.pfx per firmare.
          </p>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-200 px-4 py-3">
          <button type="button" onClick={onClose} className="rounded bg-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-300">
            Annulla
          </button>
          <button
            type="button"
            onClick={handleSign}
            disabled={loading}
            className="rounded bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 disabled:opacity-50"
          >
            {loading ? 'Firma in corso...' : 'Firma'}
          </button>
        </div>
      </div>
    </div>
  )
}
