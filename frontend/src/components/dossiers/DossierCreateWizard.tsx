import { useState, useEffect, useRef } from 'react'
import type { CreateDossierPayload } from '../../services/dossierService'
import { createDossier } from '../../services/dossierService'
import { getMetadataStructures } from '../../services/metadataService'
import type { MetadataStructure } from '../../types/metadata'
import { getUsers } from '../../services/userService'
import { getOrganizationalUnits } from '../../services/organizationService'
import { ClassificationSelect } from '../archive/ClassificationSelect'
import { DynamicMetadataForm } from '../metadata/DynamicMetadataForm'

interface DossierCreateWizardProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

type Step = 1 | 2 | 3

export function DossierCreateWizard({ isOpen, onClose, onSuccess }: DossierCreateWizardProps) {
  const [step, setStep] = useState<Step>(1)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [responsibleId, setResponsibleId] = useState('')
  const [responsibleSearch, setResponsibleSearch] = useState('')
  const [responsibleDropdownOpen, setResponsibleDropdownOpen] = useState(false)
  const responsibleRef = useRef<HTMLDivElement>(null)
  const [ouId, setOuId] = useState('')
  const [classificationCode, setClassificationCode] = useState('')
  const [classificationLabel, setClassificationLabel] = useState('')
  const [retentionYears, setRetentionYears] = useState<number>(10)
  const [retentionBasis, setRetentionBasis] = useState('')
  const [metadataStructureId, setMetadataStructureId] = useState<string | null>(null)
  const [metadataValues, setMetadataValues] = useState<Record<string, unknown>>({})
  const [metadataStructures, setMetadataStructures] = useState<MetadataStructure[]>([])
  const [users, setUsers] = useState<
    {
      id: string
      email: string
      first_name?: string
      last_name?: string
      organizational_units?: Array<{ id: string; name: string; code: string }>
    }[]
  >([])
  const [ous, setOus] = useState<{ id: string; name: string; code: string }[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      getMetadataStructures({ applicable_to: 'dossier' }).then((r) => setMetadataStructures(r.results ?? []))
      getUsers({}).then((r) => setUsers(r.results ?? []))
      getOrganizationalUnits({}).then((r) => setOus(r.results ?? []))
    }
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) {
      setStep(1)
      setTitle('')
      setDescription('')
      setResponsibleId('')
      setResponsibleSearch('')
      setResponsibleDropdownOpen(false)
      setOuId('')
      setClassificationCode('')
      setClassificationLabel('')
      setRetentionYears(10)
      setRetentionBasis('')
      setMetadataStructureId(null)
      setMetadataValues({})
      setError(null)
    }
  }, [isOpen])

  const handleClassificationChange = (code: string, label: string, retentionYears?: number) => {
    setClassificationCode(code)
    setClassificationLabel(label)
    if (retentionYears != null) setRetentionYears(retentionYears)
  }

  const handleCreate = async () => {
    setError(null)
    if (!title.trim()) {
      setError('Titolo obbligatorio.')
      return
    }
    if (!ouId.trim()) {
      setError('Seleziona un\'unità organizzativa per generare il codice identificativo.')
      return
    }
    setLoading(true)
    try {
      const payload: CreateDossierPayload = {
        title: title.trim(),
        description: description.trim() || undefined,
        responsible: responsibleId || undefined,
        organizational_unit: ouId,
        classification_code: classificationCode || undefined,
        classification_label: classificationLabel || undefined,
        retention_years: retentionYears,
        retention_basis: retentionBasis || undefined,
        metadata_structure_id: metadataStructureId || undefined,
        metadata_values: Object.keys(metadataValues).length ? metadataValues : undefined,
      }
      await createDossier(payload)
      onSuccess()
      onClose()
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : 'Errore.'
      setError(Array.isArray(msg) ? msg[0] : String(msg || 'Errore'))
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  const ou = ous.find((o) => o.id === ouId)
  const previewIdentifier = ou ? `${new Date().getFullYear()}/${ou.code}/XXXX` : '—'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" role="dialog" aria-modal="true" aria-labelledby="dossier-wizard-title">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h2 id="dossier-wizard-title" className="mb-4 text-lg font-semibold text-slate-800">
          Nuovo fascicolo — Step {step}/3
        </h2>
        <div className="mb-4 flex gap-2">
          {([1, 2, 3] as Step[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setStep(s)}
              className={`rounded px-2 py-1 text-sm font-medium ${step === s ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-600'}`}
            >
              {s}
            </button>
          ))}
        </div>

        {step === 1 && (
          <div className="flex flex-col gap-3">
            {error && <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</div>}
            <div>
              <label className="block text-sm font-medium text-slate-700">Oggetto / Titolo *</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={500}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Responsabile *</label>
              <select
                value={responsibleId}
                onChange={(e) => setResponsibleId(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">— Seleziona —</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.email} {u.first_name ? `(${u.first_name} ${u.last_name || ''})` : ''}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Unità organizzativa *</label>
              <select
                value={ouId}
                onChange={(e) => setOuId(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">— Seleziona —</option>
                {ous.map((o) => (
                  <option key={o.id} value={o.id}>{o.code} — {o.name}</option>
                ))}
              </select>
              <p className="mt-1 text-xs text-slate-500">Il codice identificativo sarà generato automaticamente (ANNO/U.O./PROGRESSIVO).</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Classificazione (titolario)</label>
              <ClassificationSelect
                value={classificationCode}
                onChange={handleClassificationChange}
                placeholder="Seleziona classificazione"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Descrizione</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="flex flex-col gap-3">
            {metadataStructures.length > 0 ? (
              <>
                <p className="text-sm text-slate-600">Opzionale: seleziona una struttura metadati per il fascicolo.</p>
                <select
                  value={metadataStructureId ?? ''}
                  onChange={(e) => {
                    setMetadataStructureId(e.target.value || null)
                    setMetadataValues({})
                  }}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">— Nessuna —</option>
                  {metadataStructures.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
                {metadataStructureId && (() => {
                  const structure = metadataStructures.find((s) => s.id === metadataStructureId)
                  return structure ? (
                    <DynamicMetadataForm
                      structure={structure}
                      values={metadataValues}
                      onChange={setMetadataValues}
                      errors={{}}
                    />
                  ) : null
                })()}
              </>
            ) : (
              <p className="text-sm text-slate-500">Nessuna struttura metadati disponibile per i fascicoli. Puoi procedere al riepilogo.</p>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="flex flex-col gap-3">
            {error && <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</div>}
            <div className="rounded border border-slate-200 bg-slate-50 p-3 text-sm">
              <p><strong>Oggetto:</strong> {title || '—'}</p>
              <p>
                <strong>Responsabile:</strong>{' '}
                {(() => {
                  const u = users.find((x) => x.id === responsibleId)
                  if (!u) return '—'
                  const ous = u.organizational_units
                  return `${u.first_name || ''} ${u.last_name || ''} (${u.email})${ous && ous.length > 0 ? ` — U.O.: ${ous.map((o) => o.name).join(', ')}` : ''}`
                })()}
              </p>
              <p><strong>U.O.:</strong> {ou?.name ?? '—'}</p>
              <p><strong>Codice identificativo (anteprima):</strong> <span className="font-mono">{previewIdentifier}</span></p>
              {classificationCode && <p><strong>Classificazione:</strong> {classificationCode} {classificationLabel}</p>}
              {classificationCode && <p><strong>Conservazione:</strong> {retentionYears} anni</p>}
            </div>
            <p className="text-xs text-slate-500">Dopo la creazione potrai aggiungere documenti, protocolli e email al fascicolo.</p>
          </div>
        )}

        <div className="mt-4 flex justify-end gap-2">
          {step > 1 ? (
            <button type="button" onClick={() => setStep((step - 1) as Step)} className="rounded bg-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-300">
              Indietro
            </button>
          ) : (
            <button type="button" onClick={onClose} className="rounded bg-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-300">
              Annulla
            </button>
          )}
          {step < 3 ? (
            <button
              type="button"
              onClick={() => step === 1 && title.trim() && ouId ? setStep(2) : step === 2 && setStep(3)}
              disabled={step === 1 && (!title.trim() || !ouId)}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              Avanti
            </button>
          ) : (
            <button type="button" onClick={handleCreate} disabled={loading} className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
              {loading ? 'Creazione...' : 'Crea fascicolo'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
