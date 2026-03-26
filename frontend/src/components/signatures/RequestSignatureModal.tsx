import { useState, useEffect, useCallback } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useModalEscape } from '../../hooks/useModalAccessibility'
import { getUsers } from '../../services/userService'
import { requestForProtocol, requestForDossier } from '../../services/signatureService'
import type { SignatureTargetType } from '../../types/signatures'

interface RequestSignatureModalProps {
  open: boolean
  targetType: SignatureTargetType
  targetId: string
  onClose: () => void
  onSuccess: () => void
}

interface SignerRow {
  user_id: string
  order: number
  role_required: string
}

export function RequestSignatureModal({
  open,
  targetType,
  targetId,
  onClose,
  onSuccess,
}: RequestSignatureModalProps) {
  const [users, setUsers] = useState<{ id: string; email: string; first_name?: string; last_name?: string }[]>([])
  const [signatureType, setSignatureType] = useState<'cades' | 'pades_invisible' | 'pades_graphic'>('cades')
  const [signers, setSigners] = useState<SignerRow[]>([{ user_id: '', order: 0, role_required: 'any' }])
  const [requireSequential, setRequireSequential] = useState(false)
  const [signAllDocuments, setSignAllDocuments] = useState(false)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (open) {
      getUsers({}).then((r) => setUsers(r.results ?? []))
    }
  }, [open])

  const addSigner = () => {
    setSigners((s) => [...s, { user_id: '', order: s.length, role_required: 'any' }])
  }

  const removeSigner = (i: number) => {
    setSigners((s) => s.filter((_, idx) => idx !== i))
  }

  const updateSigner = (i: number, field: keyof SignerRow, value: string | number) => {
    setSigners((s) => s.map((row, idx) => (idx === i ? { ...row, [field]: value } : row)))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const signersPayload = signers
      .map((s, i) => ({ user_id: s.user_id, order: i, role_required: s.role_required || 'any' }))
      .filter((s) => s.user_id)
    if (signersPayload.length === 0) {
      alert('Seleziona almeno un firmatario')
      return
    }
    setSubmitting(true)
    try {
      if (targetType === 'protocol') {
        await requestForProtocol({
          protocol_id: targetId,
          signers: signersPayload,
          signature_type: signatureType,
          require_sequential: requireSequential,
          sign_all_documents: signAllDocuments,
          notes,
        })
      } else if (targetType === 'dossier') {
        await requestForDossier({
          dossier_id: targetId,
          signers: signersPayload,
          signature_type: signatureType,
          require_sequential: requireSequential,
          sign_all_documents: signAllDocuments,
          notes,
        })
      }
      onSuccess()
    } catch (err) {
      alert((err as Error)?.message || 'Errore creazione richiesta firma')
    } finally {
      setSubmitting(false)
    }
  }

  const modalRef = useFocusTrap(open)
  const closeCb = useCallback(() => onClose(), [onClose])
  useModalEscape(open, closeCb)

  if (!open) return null

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
        aria-labelledby="modal-title-request-signature"
        className="w-full max-w-lg rounded-lg bg-white shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 id="modal-title-request-signature" className="text-lg font-semibold text-slate-800">
            Richiedi firma
          </h2>
          <button type="button" onClick={onClose} className="rounded p-1 text-slate-500 hover:bg-slate-100">
            ✕
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Tipo firma</label>
            <div className="flex gap-4">
              {(['cades', 'pades_invisible', 'pades_graphic'] as const).map((t) => (
                <label key={t} className="flex items-center gap-1">
                  <input
                    type="radio"
                    name="signatureType"
                    checked={signatureType === t}
                    onChange={() => setSignatureType(t)}
                  />
                  <span className="text-sm">{t === 'cades' ? 'CAdES' : t === 'pades_invisible' ? 'PAdES invisibile' : 'PAdES grafica'}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <div className="mb-1 flex items-center justify-between">
              <label className="text-sm font-medium text-slate-700">Firmatari</label>
              <button type="button" onClick={addSigner} className="text-xs text-indigo-600 hover:underline">
                + Aggiungi
              </button>
            </div>
            {signers.map((row, i) => (
              <div key={i} className="mb-2 flex gap-2 items-center">
                <select
                  value={row.user_id}
                  onChange={(e) => updateSigner(i, 'user_id', e.target.value)}
                  className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm"
                >
                  <option value="">— Seleziona utente —</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.email} {u.first_name ? `(${u.first_name} ${u.last_name || ''})` : ''}
                    </option>
                  ))}
                </select>
                <select
                  value={row.role_required}
                  onChange={(e) => updateSigner(i, 'role_required', e.target.value)}
                  className="w-28 rounded border border-slate-300 px-2 py-1.5 text-sm"
                >
                  <option value="any">Qualsiasi</option>
                  <option value="operator">Operatore</option>
                  <option value="reviewer">Revisore</option>
                  <option value="approver">Approvatore</option>
                  <option value="admin">Admin</option>
                </select>
                {signers.length > 1 && (
                  <button type="button" onClick={() => removeSigner(i)} className="text-red-600 text-xs">
                    Rimuovi
                  </button>
                )}
              </div>
            ))}
          </div>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={requireSequential} onChange={(e) => setRequireSequential(e.target.checked)} />
            <span className="text-sm text-slate-700">Firma sequenziale</span>
          </label>
          {(targetType === 'protocol' || targetType === 'dossier') && (
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={signAllDocuments} onChange={(e) => setSignAllDocuments(e.target.checked)} />
              <span className="text-sm text-slate-700">Firma tutti i documenti allegati</span>
            </label>
          )}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Note</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
              rows={2}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="rounded bg-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-300">
              Annulla
            </button>
            <button type="submit" disabled={submitting} className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50">
              {submitting ? 'Invio...' : 'Richiedi firma'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
