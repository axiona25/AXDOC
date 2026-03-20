import { useState, useEffect } from 'react'
import type { CreateProtocolPayload } from '../../services/protocolService'
import { createProtocolWithFile } from '../../services/protocolService'
import type { OrganizationalUnit } from '../../services/organizationService'
import { getOrganizationalUnits } from '../../services/organizationService'
import type { DocumentItem } from '../../services/documentService'
import { getDocuments } from '../../services/documentService'
import { getDossiers } from '../../services/dossierService'
import type { DossierItem } from '../../services/dossierService'

interface ProtocolFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (payload: CreateProtocolPayload) => Promise<void>
  linkedDocument?: DocumentItem | null
  documents?: DocumentItem[]
}

const STEPS = [
  'Informazioni base',
  'Dettagli',
  'Fascicoli',
  'Allegati',
  'Riepilogo',
]

const CATEGORY_OPTIONS = [
  { value: 'file', label: 'Documento/File' },
  { value: 'email', label: 'Email' },
  { value: 'pec', label: 'PEC' },
  { value: 'other', label: 'Altro' },
]

function formatApiError(err: unknown): string {
  if (!err || typeof err !== 'object' || !('response' in err)) return 'Errore durante la creazione.'
  const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data
  if (!data) return 'Errore durante la creazione.'
  if (typeof data.detail === 'string') return data.detail
  if (Array.isArray(data.detail)) return String(data.detail[0])
  const firstKey = Object.keys(data)[0]
  if (firstKey) {
    const v = data[firstKey]
    if (typeof v === 'string') return v
    if (Array.isArray(v)) return String(v[0])
  }
  return 'Errore durante la creazione.'
}

export function ProtocolFormModal({
  isOpen,
  onClose,
  onSubmit,
  linkedDocument,
}: ProtocolFormModalProps) {
  const [step, setStep] = useState(0)
  const [direction, setDirection] = useState<'in' | 'out'>('in')
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('file')
  const [senderReceiver, setSenderReceiver] = useState('')
  const [organizationalUnitId, setOrganizationalUnitId] = useState('')
  const [notes, setNotes] = useState('')
  const [dossierIds, setDossierIds] = useState<string[]>([])
  const [dossiers, setDossiers] = useState<DossierItem[]>([])
  const [attachmentIds, setAttachmentIds] = useState<string[]>([])
  const [availableDocs, setAvailableDocs] = useState<DocumentItem[]>([])
  const [fileFromPc, setFileFromPc] = useState<File | null>(null)
  const [ous, setOus] = useState<OrganizationalUnit[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createdProtocol, setCreatedProtocol] = useState<{ protocol_id: string; registered_at: string } | null>(null)

  useEffect(() => {
    if (isOpen) {
      setStep(0)
      setDirection(linkedDocument ? 'out' : 'in')
      setSubject(linkedDocument?.title || '')
      setDescription('')
      setCategory('file')
      setSenderReceiver('')
      setOrganizationalUnitId('')
      setNotes('')
      setDossierIds([])
      setAttachmentIds([])
      setFileFromPc(null)
      setError(null)
      setCreatedProtocol(null)
      setLoading(false)
      getOrganizationalUnits({}).then((r) => setOus(r.results || [])).catch(() => setOus([]))
      getDossiers({ status: 'open' }).then((r) => setDossiers(r.results || [])).catch(() => setDossiers([]))
      getDocuments({ page: 1 }).then((r) => setAvailableDocs(r.results || [])).catch(() => setAvailableDocs([]))
    }
  }, [isOpen, linkedDocument])

  const canGoNext = (): boolean => {
    if (step === 0) return !!subject.trim() && !!category
    if (step === 1) return !!organizationalUnitId
    return true
  }

  const handleNext = () => {
    setError(null)
    if (step < STEPS.length - 1) setStep(step + 1)
  }

  const handleBack = () => {
    setError(null)
    if (step > 0) setStep(step - 1)
  }

  const handleSubmit = async () => {
    setError(null)
    setLoading(true)
    try {
      const payload: CreateProtocolPayload = {
        direction,
        subject: subject.trim(),
        description: description.trim() || undefined,
        category,
        sender_receiver: senderReceiver.trim() || undefined,
        organizational_unit: organizationalUnitId,
        notes: notes.trim() || undefined,
        attachment_ids: attachmentIds.length > 0 ? attachmentIds : undefined,
        dossier_ids: dossierIds.length > 0 ? dossierIds : undefined,
      }
      if (linkedDocument) payload.document = linkedDocument.id

      const result = await createProtocolWithFile(payload, fileFromPc || undefined)
      setCreatedProtocol({
        protocol_id: result.protocol_id,
        registered_at: result.registered_at || result.created_at,
      })
      if (step !== STEPS.length - 1) setStep(STEPS.length - 1)
      await onSubmit(payload).catch(() => {})
    } catch (err: unknown) {
      setError(formatApiError(err))
    } finally {
      setLoading(false)
    }
  }

  const toggleDossier = (id: string) => {
    setDossierIds((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]))
  }

  const toggleAttachment = (id: string) => {
    setAttachmentIds((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]))
  }

  const ouName = ous.find((o) => o.id === organizationalUnitId)?.name || '—'

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" role="dialog" aria-modal="true">
      <div className="flex w-full max-w-2xl flex-col rounded-lg bg-white shadow-xl" style={{ maxHeight: '85vh' }}>
        <div className="border-b border-slate-200 px-6 pb-4 pt-5">
          <h2 className="mb-3 text-lg font-semibold text-slate-800">
            {linkedDocument ? 'Protocolla documento' : 'Nuovo protocollo'}
          </h2>
          <div className="flex flex-wrap items-center gap-1">
            {STEPS.map((label, i) => (
              <div key={label} className="flex items-center">
                <div
                  className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium ${
                    i < step ? 'bg-green-500 text-white' : i === step ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  {i < step ? '✓' : i + 1}
                </div>
                <span
                  className={`ml-1 hidden text-xs sm:inline ${i === step ? 'font-medium text-indigo-700' : 'text-slate-400'}`}
                >
                  {label}
                </span>
                {i < STEPS.length - 1 && <div className="mx-2 h-px w-4 bg-slate-300" />}
              </div>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {error && <div className="mb-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

          {step === 0 && (
            <div className="flex flex-col gap-4">
              {!linkedDocument && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Direzione *</label>
                  <div className="flex gap-2">
                    {(['in', 'out'] as const).map((d) => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => setDirection(d)}
                        className={`flex-1 rounded border px-4 py-2 text-sm font-medium transition-colors ${
                          direction === d
                            ? d === 'in'
                              ? 'border-blue-500 bg-blue-50 text-blue-700'
                              : 'border-amber-500 bg-amber-50 text-amber-700'
                            : 'border-slate-300 text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        {d === 'in' ? '📥 In entrata' : '📤 In uscita'}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Oggetto *</label>
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  maxLength={500}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  placeholder="Oggetto del protocollo"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Descrizione</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  placeholder="Descrizione estesa (facoltativa)"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Categoria *</label>
                <div className="grid grid-cols-2 gap-2">
                  {CATEGORY_OPTIONS.map((c) => (
                    <button
                      key={c.value}
                      type="button"
                      onClick={() => setCategory(c.value)}
                      className={`rounded border px-3 py-2 text-sm font-medium transition-colors ${
                        category === c.value
                          ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                          : 'border-slate-300 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="flex flex-col gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  {direction === 'in' ? 'Mittente' : 'Destinatario'}
                </label>
                <input
                  type="text"
                  value={senderReceiver}
                  onChange={(e) => setSenderReceiver(e.target.value)}
                  maxLength={500}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Unità organizzativa *</label>
                <select
                  value={organizationalUnitId}
                  onChange={(e) => setOrganizationalUnitId(e.target.value)}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">Seleziona UO</option>
                  {ous.map((ou) => (
                    <option key={ou.id} value={ou.id}>
                      {ou.name} ({ou.code})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Note</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-slate-600">Seleziona i fascicoli a cui associare il protocollo (facoltativo).</p>
              {dossiers.length === 0 ? (
                <p className="py-4 text-center text-slate-400">Nessun fascicolo aperto disponibile.</p>
              ) : (
                <div className="max-h-60 overflow-y-auto rounded border border-slate-200">
                  {dossiers.map((d) => (
                    <label
                      key={d.id}
                      className={`flex cursor-pointer items-center gap-3 border-b border-slate-100 px-3 py-2 hover:bg-slate-50 ${
                        dossierIds.includes(d.id) ? 'bg-indigo-50' : ''
                      }`}
                    >
                      <input type="checkbox" checked={dossierIds.includes(d.id)} onChange={() => toggleDossier(d.id)} />
                      <div>
                        <p className="text-sm font-medium text-slate-800">{d.title}</p>
                        <p className="text-xs text-slate-500">{d.identifier || d.id}</p>
                      </div>
                    </label>
                  ))}
                </div>
              )}
              {dossierIds.length > 0 && (
                <p className="text-xs text-indigo-600">
                  {dossierIds.length} fascicol{dossierIds.length === 1 ? 'o' : 'i'} selezionat{dossierIds.length === 1 ? 'o' : 'i'}
                </p>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="flex flex-col gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Carica file dal PC</label>
                <input type="file" onChange={(e) => setFileFromPc(e.target.files?.[0] || null)} className="w-full text-sm" />
                {fileFromPc && <p className="mt-1 text-xs text-green-600">📎 {fileFromPc.name}</p>}
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Oppure allega dalla sezione Documenti</label>
                {availableDocs.length === 0 ? (
                  <p className="py-4 text-center text-slate-400">Nessun documento disponibile.</p>
                ) : (
                  <div className="max-h-48 overflow-y-auto rounded border border-slate-200">
                    {availableDocs.map((doc) => (
                      <label
                        key={doc.id}
                        className={`flex cursor-pointer items-center gap-3 border-b border-slate-100 px-3 py-2 hover:bg-slate-50 ${
                          attachmentIds.includes(doc.id) ? 'bg-indigo-50' : ''
                        }`}
                      >
                        <input type="checkbox" checked={attachmentIds.includes(doc.id)} onChange={() => toggleAttachment(doc.id)} />
                        <div>
                          <p className="text-sm font-medium text-slate-800">{doc.title}</p>
                          <p className="text-xs text-slate-500">
                            {doc.updated_at ? new Date(doc.updated_at).toLocaleDateString('it-IT') : ''}
                          </p>
                        </div>
                      </label>
                    ))}
                  </div>
                )}
                {attachmentIds.length > 0 && (
                  <p className="mt-1 text-xs text-indigo-600">
                    {attachmentIds.length} allegat{attachmentIds.length === 1 ? 'o' : 'i'} selezionat
                    {attachmentIds.length === 1 ? 'o' : 'i'}
                  </p>
                )}
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="flex flex-col gap-3">
              {createdProtocol ? (
                <div className="rounded-lg border-2 border-green-200 bg-green-50 p-4 text-center">
                  <p className="text-lg font-bold text-green-800">Protocollo creato!</p>
                  <p className="mt-2 font-mono text-2xl text-green-700">{createdProtocol.protocol_id}</p>
                  <p className="mt-1 text-sm text-green-600">
                    Registrato il {new Date(createdProtocol.registered_at).toLocaleString('it-IT')}
                  </p>
                </div>
              ) : (
                <>
                  <h3 className="text-sm font-semibold text-slate-700">Riepilogo protocollo</h3>
                  <div className="rounded border border-slate-200 bg-slate-50 p-3 text-sm">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <span className="text-slate-500">Direzione:</span>{' '}
                        <strong>{direction === 'in' ? 'In entrata' : 'In uscita'}</strong>
                      </div>
                      <div>
                        <span className="text-slate-500">Categoria:</span>{' '}
                        <strong>{CATEGORY_OPTIONS.find((c) => c.value === category)?.label}</strong>
                      </div>
                      <div className="col-span-2">
                        <span className="text-slate-500">Oggetto:</span> <strong>{subject}</strong>
                      </div>
                      {description && (
                        <div className="col-span-2">
                          <span className="text-slate-500">Descrizione:</span> {description}
                        </div>
                      )}
                      <div>
                        <span className="text-slate-500">{direction === 'in' ? 'Mittente' : 'Destinatario'}:</span>{' '}
                        {senderReceiver || '—'}
                      </div>
                      <div>
                        <span className="text-slate-500">UO:</span> {ouName}
                      </div>
                      {notes && (
                        <div className="col-span-2">
                          <span className="text-slate-500">Note:</span> {notes}
                        </div>
                      )}
                      <div>
                        <span className="text-slate-500">Fascicoli:</span> {dossierIds.length || 'Nessuno'}
                      </div>
                      <div>
                        <span className="text-slate-500">Allegati:</span>{' '}
                        {attachmentIds.length + (fileFromPc ? 1 : 0) || 'Nessuno'}
                      </div>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500">
                    Il numero di protocollo e la data/ora saranno assegnati automaticamente alla conferma.
                  </p>
                </>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 px-6 py-3">
          <button
            type="button"
            onClick={createdProtocol ? onClose : step === 0 ? onClose : handleBack}
            className="rounded bg-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-300"
          >
            {createdProtocol ? 'Chiudi' : step === 0 ? 'Annulla' : '← Indietro'}
          </button>
          {!createdProtocol &&
            (step < STEPS.length - 1 ? (
              <button
                type="button"
                onClick={handleNext}
                disabled={!canGoNext()}
                className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                Avanti →
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={loading}
                className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? 'Creazione...' : '✓ Crea protocollo'}
              </button>
            ))}
        </div>
      </div>
    </div>
  )
}
