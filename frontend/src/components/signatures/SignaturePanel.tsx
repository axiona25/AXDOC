import { useState, useEffect } from 'react'
import {
  getSignaturesByTarget,
  signStep,
  rejectStep,
  downloadSigned,
  verifySignatureValidity,
} from '../../services/signatureService'
import type { SignatureRequestItem } from '../../types/signatures'
import { RequestSignatureModal } from './RequestSignatureModal'
import { SignNowModal } from './SignNowModal'
import { RejectSignatureModal } from './RejectSignatureModal'
import { VerificationResultModal } from './VerificationResultModal'

interface SignaturePanelProps {
  targetType: 'document' | 'protocol' | 'dossier'
  targetId: string
  canRequestSignature: boolean
  currentUserId: string
}

const STATUS_LABEL: Record<string, string> = {
  pending_otp: 'In attesa',
  pending_provider: 'In elaborazione',
  completed: 'Completata',
  failed: 'Fallita',
  expired: 'Scaduta',
  rejected: 'Rifiutata',
}

const STEP_STATUS_ICON: Record<string, string> = {
  pending: '⏳',
  signed: '✅',
  rejected: '❌',
  skipped: '⊘',
}

export function SignaturePanel({
  targetType,
  targetId,
  canRequestSignature,
  currentUserId,
}: SignaturePanelProps) {
  const [requests, setRequests] = useState<SignatureRequestItem[]>([])
  const [loading, setLoading] = useState(true)
  const [requestModalOpen, setRequestModalOpen] = useState(false)
  const [signModalSig, setSignModalSig] = useState<SignatureRequestItem | null>(null)
  const [rejectModalSig, setRejectModalSig] = useState<SignatureRequestItem | null>(null)
  const [verifyResult, setVerifyResult] = useState<Record<string, unknown> | null>(null)
  const [verifySigId, setVerifySigId] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    getSignaturesByTarget(targetType, targetId)
      .then(setRequests)
      .catch(() => setRequests([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [targetType, targetId])

  const activeRequests = requests.filter(
    (r) => r.status !== 'completed' && r.status !== 'rejected' && r.status !== 'failed' && r.status !== 'expired'
  )
  const completedRequests = requests.filter((r) => r.status === 'completed')

  const isCurrentSigner = (sig: SignatureRequestItem) => {
    const cur = sig.current_signer
    return cur && String(cur.id) === String(currentUserId)
  }

  const handleRequestSuccess = () => {
    setRequestModalOpen(false)
    load()
  }

  const handleSignNow = async (simulate = false) => {
    if (!signModalSig) return
    try {
      await signStep(signModalSig.id, simulate ? { certificate_info: { mock: true } } : {})
      setSignModalSig(null)
      load()
    } catch (e) {
      alert((e as Error)?.message || 'Errore firma')
    }
  }

  const handleReject = async (reason: string) => {
    if (!rejectModalSig) return
    try {
      await rejectStep(rejectModalSig.id, reason)
      setRejectModalSig(null)
      load()
    } catch (e) {
      alert((e as Error)?.message || 'Errore')
    }
  }

  const handleDownload = async (sig: SignatureRequestItem) => {
    try {
      const blob = await downloadSigned(sig.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `signed_${sig.id}.p7m`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      alert('Download non disponibile')
    }
  }

  const handleVerify = async (sigId: string) => {
    try {
      const result = await verifySignatureValidity(sigId)
      setVerifyResult(result as Record<string, unknown>)
      setVerifySigId(sigId)
    } catch {
      setVerifyResult({ valid: false, error: 'Verifica non disponibile' })
      setVerifySigId(sigId)
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Caricamento firme...</p>

  return (
    <div className="space-y-6">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-medium text-slate-700">Firme attive</h3>
          {canRequestSignature && (
            <button
              type="button"
              onClick={() => setRequestModalOpen(true)}
              className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700"
            >
              Richiedi firma
            </button>
          )}
        </div>
        {activeRequests.length === 0 ? (
          <p className="text-sm text-slate-500">Nessuna firma richiesta.</p>
        ) : (
          <ul className="space-y-3">
            {activeRequests.map((sig) => (
              <li key={sig.id} className="rounded border border-slate-200 bg-slate-50 p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-slate-800">
                      {sig.format === 'cades' ? 'CAdES' : sig.format === 'pades_invisible' ? 'PAdES invisibile' : 'PAdES grafica'}
                    </span>
                    <span className="ml-2 text-xs text-slate-500">
                      Richiedente: {sig.requested_by_email} · {sig.created_at ? new Date(sig.created_at).toLocaleDateString() : ''}
                    </span>
                  </div>
                  <span className="rounded px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-800">
                    {STATUS_LABEL[sig.status] ?? sig.status}
                  </span>
                </div>
                {sig.sequence_steps && sig.sequence_steps.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {sig.sequence_steps.map((step) => (
                      <span
                        key={step.id}
                        className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 text-xs"
                        title={step.signer_email}
                      >
                        {STEP_STATUS_ICON[step.status] ?? '?'} {step.signer_email ?? step.signer}
                      </span>
                    ))}
                  </div>
                )}
                <div className="mt-2 flex flex-wrap gap-2">
                  {isCurrentSigner(sig) && sig.status !== 'rejected' && (
                    <>
                      <button
                        type="button"
                        onClick={() => setSignModalSig(sig)}
                        className="rounded bg-green-600 px-2 py-1 text-xs text-white hover:bg-green-700"
                      >
                        Firma ora
                      </button>
                      <button
                        type="button"
                        onClick={() => setRejectModalSig(sig)}
                        className="rounded bg-red-100 px-2 py-1 text-xs text-red-700 hover:bg-red-200"
                      >
                        Rifiuta
                      </button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {completedRequests.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium text-slate-700">Storico firme completate</h3>
          <ul className="space-y-2">
            {completedRequests.map((sig) => (
              <li key={sig.id} className="flex items-center justify-between rounded border border-slate-100 px-3 py-2 text-sm">
                <span>
                  {sig.format} · {sig.requested_by_email} · {sig.signed_at ? new Date(sig.signed_at).toLocaleDateString() : ''}
                </span>
                <div className="flex gap-2">
                  <button type="button" onClick={() => handleDownload(sig)} className="text-indigo-600 hover:underline text-xs">
                    Scarica firmato
                  </button>
                  <button type="button" onClick={() => handleVerify(sig.id)} className="text-slate-600 hover:underline text-xs">
                    Verifica firma
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <RequestSignatureModal
        targetType={targetType}
        targetId={targetId}
        onClose={() => setRequestModalOpen(false)}
        onSuccess={handleRequestSuccess}
        open={requestModalOpen}
      />
      {signModalSig && (
        <SignNowModal
          signatureRequest={signModalSig}
          onClose={() => setSignModalSig(null)}
          onSign={handleSignNow}
        />
      )}
      {rejectModalSig && (
        <RejectSignatureModal
          onClose={() => setRejectModalSig(null)}
          onReject={handleReject}
        />
      )}
      {verifyResult !== null && verifySigId && (
        <VerificationResultModal
          result={verifyResult}
          onClose={() => { setVerifyResult(null); setVerifySigId(null) }}
        />
      )}
    </div>
  )
}
