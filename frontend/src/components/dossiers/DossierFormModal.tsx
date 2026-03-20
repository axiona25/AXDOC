import { useState, useEffect } from 'react'
import type { CreateDossierPayload, DossierDetailItem } from '../../services/dossierService'
import { getMetadataStructures } from '../../services/metadataService'
import type { MetadataStructure } from '../../types/metadata'
import { DynamicMetadataForm } from '../metadata/DynamicMetadataForm'

interface DossierFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (payload: CreateDossierPayload) => Promise<void>
  initial?: DossierDetailItem | null
  /** Per edit: lista utenti per select responsabile (opzionale) */
  users?: { id: string; email: string; first_name?: string; last_name?: string }[]
}

export function DossierFormModal({
  isOpen,
  onClose,
  onSubmit,
  initial,
  users = [],
}: DossierFormModalProps) {
  const [title, setTitle] = useState('')
  const [identifier, setIdentifier] = useState('')
  const [description, setDescription] = useState('')
  const [responsibleId, setResponsibleId] = useState('')
  const [allowedUserIds, setAllowedUserIds] = useState<string[]>([])
  const [allowedOuIds, setAllowedOuIds] = useState<string[]>([])
  const [metadataStructureId, setMetadataStructureId] = useState<string | null>(null)
  const [metadataValues, setMetadataValues] = useState<Record<string, unknown>>({})
  const [metadataStructures, setMetadataStructures] = useState<MetadataStructure[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      getMetadataStructures({ applicable_to: 'dossier' }).then((r) => setMetadataStructures(r.results ?? []))
    }
  }, [isOpen])

  useEffect(() => {
    if (initial) {
      setTitle(initial.title)
      setIdentifier(initial.identifier)
      setDescription(initial.description || '')
      setResponsibleId(initial.responsible || '')
      setAllowedUserIds(initial.allowed_user_ids || [])
      setAllowedOuIds(initial.allowed_ou_ids || [])
      const metaId = typeof initial.metadata_structure === 'object' && initial.metadata_structure != null
        ? (initial.metadata_structure as { id: string }).id
        : (initial.metadata_structure as string) || null
      setMetadataStructureId(metaId)
      setMetadataValues(initial.metadata_values ?? {})
    } else {
      setTitle('')
      setIdentifier('')
      setDescription('')
      setResponsibleId('')
      setAllowedUserIds([])
      setAllowedOuIds([])
      setMetadataStructureId(null)
      setMetadataValues({})
    }
  }, [initial, isOpen])


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!title.trim()) {
      setError('Titolo obbligatorio.')
      return
    }
    if (!identifier.trim()) {
      setError('Identificatore obbligatorio.')
      return
    }
    setLoading(true)
    try {
      await onSubmit({
        title: title.trim(),
        identifier: identifier.trim(),
        description: description.trim() || undefined,
        responsible: responsibleId || undefined,
        allowed_users: allowedUserIds.length ? allowedUserIds : undefined,
        allowed_ous: allowedOuIds.length ? allowedOuIds : undefined,
        metadata_structure_id: metadataStructureId || undefined,
        metadata_values: Object.keys(metadataValues).length ? metadataValues : undefined,
      })
      onClose()
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string; identifier?: string } } }).response?.data?.identifier
          || (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : 'Errore.'
      setError(Array.isArray(msg) ? msg[0] : String(msg || 'Errore'))
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" role="dialog" aria-modal="true" aria-labelledby="dossier-form-title">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h2 id="dossier-form-title" className="mb-4 text-lg font-semibold text-slate-800">
          {initial ? 'Modifica fascicolo' : 'Nuovo fascicolo'}
        </h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          {error && (
            <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</div>
          )}
          <div>
            <label htmlFor="dossier-title" className="block text-sm font-medium text-slate-700">Titolo *</label>
            <input
              id="dossier-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={500}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              required
            />
          </div>
          <div>
            <label htmlFor="dossier-identifier" className="block text-sm font-medium text-slate-700">Identificatore *</label>
            <input
              id="dossier-identifier"
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              maxLength={100}
              placeholder="es. CONTR-2024"
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              required
              readOnly={!!initial}
            />
          </div>
          <div>
            <label htmlFor="dossier-description" className="block text-sm font-medium text-slate-700">Descrizione</label>
            <textarea
              id="dossier-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="dossier-responsible" className="block text-sm font-medium text-slate-700">Responsabile</label>
            <select
              id="dossier-responsible"
              value={responsibleId}
              onChange={(e) => setResponsibleId(e.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">—</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.email} {u.first_name ? `(${u.first_name} ${u.last_name || ''})` : ''}</option>
              ))}
            </select>
          </div>
          {metadataStructures.length > 0 && (
            <div className="rounded border border-slate-200 bg-slate-50 p-3">
              <p className="mb-2 text-sm font-medium text-slate-700">Metadati fascicolo</p>
              <select
                value={metadataStructureId ?? ''}
                onChange={(e) => {
                  setMetadataStructureId(e.target.value || null)
                  setMetadataValues({})
                }}
                className="mb-2 w-full rounded border border-slate-300 px-3 py-2 text-sm"
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
            </div>
          )}
          <div className="mt-2 flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded bg-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-300">
              Annulla
            </button>
            <button type="submit" disabled={loading} className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
              {loading ? 'Salvataggio...' : initial ? 'Salva' : 'Crea fascicolo'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
