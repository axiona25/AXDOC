import { useState, useCallback } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useModalEscape } from '../../hooks/useModalAccessibility'

interface RejectSignatureModalProps {
  onClose: () => void
  onReject: (reason: string) => void
}

export function RejectSignatureModal({ onClose, onReject }: RejectSignatureModalProps) {
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const modalRef = useFocusTrap(true)
  const closeCb = useCallback(() => onClose(), [onClose])
  useModalEscape(true, closeCb)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!reason.trim()) {
      alert('Inserire una motivazione')
      return
    }
    setSubmitting(true)
    onReject(reason.trim())
    setSubmitting(false)
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
        aria-labelledby="modal-title-reject-signature"
        className="w-full max-w-md rounded-lg bg-white shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 id="modal-title-reject-signature" className="text-lg font-semibold text-slate-800">
            Rifiuta firma
          </h2>
          <button type="button" onClick={onClose} className="rounded p-1 text-slate-500 hover:bg-slate-100">
            ✕
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-4">
          <label className="mb-1 block text-sm font-medium text-slate-700">Motivazione (obbligatoria)</label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
            rows={4}
            required
            placeholder="Indicare il motivo del rifiuto..."
          />
          <div className="mt-4 flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded bg-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-300">
              Annulla
            </button>
            <button
              type="submit"
              disabled={submitting || !reason.trim()}
              className="rounded bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-50"
            >
              Rifiuta
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
