import { useState } from 'react'
import { createPdv } from '../../services/archiveService'
import type { InformationPackageItem } from '../../services/archiveService'

interface PackageWizardProps {
  open: boolean
  onClose: () => void
  onSuccess: (pkg: InformationPackageItem) => void
}

const STEP_LABELS = ['Documenti', 'Protocolli', 'Fascicoli', 'Riepilogo']

export function PackageWizard({ open, onClose, onSuccess }: PackageWizardProps) {
  const [step, setStep] = useState(0)
  const [documentIds, setDocumentIds] = useState<string[]>([])
  const [protocolIds, setProtocolIds] = useState<string[]>([])
  const [dossierIds, setDossierIds] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleCreate = async () => {
    if (!documentIds.length && !protocolIds.length && !dossierIds.length) {
      setError('Seleziona almeno un documento, protocollo o fascicolo.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const pkg = await createPdv({
        document_ids: documentIds,
        protocol_ids: protocolIds.length ? protocolIds : undefined,
        dossier_ids: dossierIds.length ? dossierIds : undefined,
      })
      onSuccess(pkg)
      onClose()
      setStep(0)
      setDocumentIds([])
      setProtocolIds([])
      setDossierIds([])
    } catch (e) {
      setError((e as Error)?.message || 'Errore creazione pacchetto')
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-2xl rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-lg font-semibold text-slate-800">Nuovo pacchetto PdV</h2>
          <button type="button" onClick={onClose} className="rounded p-1 text-slate-500 hover:bg-slate-100">
            ✕
          </button>
        </div>
        <div className="flex gap-2 border-b border-slate-100 px-4 py-2">
          {STEP_LABELS.map((label, i) => (
            <span
              key={label}
              className={`rounded px-2 py-1 text-sm ${i === step ? 'bg-indigo-100 text-indigo-800' : 'text-slate-500'}`}
            >
              {i + 1}. {label}
            </span>
          ))}
        </div>
        <div className="p-4 min-h-[200px]">
          {step === 0 && (
            <div>
              <p className="mb-2 text-sm text-slate-600">Inserisci ID documenti (uno per riga o separati da virgola)</p>
              <textarea
                value={documentIds.join('\n')}
                onChange={(e) => setDocumentIds(e.target.value.split(/[\n,]/).map((s) => s.trim()).filter(Boolean))}
                placeholder="uuid-1&#10;uuid-2"
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm font-mono"
                rows={4}
              />
            </div>
          )}
          {step === 1 && (
            <div>
              <p className="mb-2 text-sm text-slate-600">ID protocolli (opzionale)</p>
              <textarea
                value={protocolIds.join('\n')}
                onChange={(e) => setProtocolIds(e.target.value.split(/[\n,]/).map((s) => s.trim()).filter(Boolean))}
                placeholder="uuid-1"
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm font-mono"
                rows={3}
              />
            </div>
          )}
          {step === 2 && (
            <div>
              <p className="mb-2 text-sm text-slate-600">ID fascicoli (opzionale)</p>
              <textarea
                value={dossierIds.join('\n')}
                onChange={(e) => setDossierIds(e.target.value.split(/[\n,]/).map((s) => s.trim()).filter(Boolean))}
                placeholder="uuid-1"
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm font-mono"
                rows={3}
              />
            </div>
          )}
          {step === 3 && (
            <div className="text-sm">
              <p><strong>Documenti:</strong> {documentIds.length}</p>
              <p><strong>Protocolli:</strong> {protocolIds.length}</p>
              <p><strong>Fascicoli:</strong> {dossierIds.length}</p>
              <p className="mt-2 text-slate-500">Stima: pacchetto ZIP con manifest e checksum.</p>
              {error && <p className="mt-2 text-red-600">{error}</p>}
            </div>
          )}
        </div>
        <div className="flex justify-between border-t border-slate-200 px-4 py-3">
          <button
            type="button"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
            className="rounded bg-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-300 disabled:opacity-50"
          >
            Indietro
          </button>
          {step < 3 ? (
            <button
              type="button"
              onClick={() => setStep((s) => s + 1)}
              className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
            >
              Avanti
            </button>
          ) : (
            <button
              type="button"
              onClick={handleCreate}
              disabled={loading}
              className="rounded bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 disabled:opacity-50"
            >
              {loading ? 'Creazione...' : 'Crea PdV'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
