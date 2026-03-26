import { useCallback, useEffect, useState } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useModalEscape } from '../../hooks/useModalAccessibility'
import { getFolders } from '../../services/documentService'
import { getMetadataStructures } from '../../services/metadataService'
import { getWorkflowTemplates } from '../../services/workflowService'
import type { FolderItem } from '../../services/documentService'
import type { DocumentTemplate } from '../../services/templateService'
import { createTemplate, updateTemplate } from '../../services/templateService'

interface TemplateFormModalProps {
  open: boolean
  onClose: () => void
  onSaved: () => void
  initial?: DocumentTemplate | null
}

function flatFolders(list: FolderItem[]): FolderItem[] {
  const out: FolderItem[] = []
  const visit = (items: FolderItem[]) => {
    items.forEach((f) => {
      out.push(f)
      if (f.subfolders?.length) visit(f.subfolders)
    })
  }
  visit(list)
  return out
}

export function TemplateFormModal({ open, onClose, onSaved, initial }: TemplateFormModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [defaultFolder, setDefaultFolder] = useState<string>('')
  const [defaultMeta, setDefaultMeta] = useState<string>('')
  const [defaultWorkflow, setDefaultWorkflow] = useState<string>('')
  const [autoStart, setAutoStart] = useState(false)
  const [defaultStatus, setDefaultStatus] = useState<'DRAFT' | 'IN_REVIEW'>('DRAFT')
  const [allowedExt, setAllowedExt] = useState('')
  const [maxMb, setMaxMb] = useState<string>('')
  const [isActive, setIsActive] = useState(true)
  const [folders, setFolders] = useState<FolderItem[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    getFolders({ all: 'true' }).then((t) => setFolders(flatFolders(t))).catch(() => setFolders([]))
  }, [open])

  useEffect(() => {
    if (!open) return
    if (initial) {
      setName(initial.name)
      setDescription(initial.description ?? '')
      setDefaultFolder(initial.default_folder ?? '')
      setDefaultMeta(initial.default_metadata_structure ?? '')
      setDefaultWorkflow(initial.default_workflow_template ?? '')
      setAutoStart(initial.auto_start_workflow)
      setDefaultStatus((initial.default_status as 'DRAFT' | 'IN_REVIEW') || 'DRAFT')
      setAllowedExt((initial.allowed_file_types ?? []).join(', '))
      setMaxMb(initial.max_file_size_mb != null ? String(initial.max_file_size_mb) : '')
      setIsActive(initial.is_active)
    } else {
      setName('')
      setDescription('')
      setDefaultFolder('')
      setDefaultMeta('')
      setDefaultWorkflow('')
      setAutoStart(false)
      setDefaultStatus('DRAFT')
      setAllowedExt('')
      setMaxMb('')
      setIsActive(true)
    }
    setError('')
  }, [open, initial])

  const [metaList, setMetaList] = useState<{ id: string; name: string }[]>([])
  const [wfList, setWfList] = useState<{ id: string; name: string }[]>([])

  useEffect(() => {
    if (!open) return
    getMetadataStructures({ applicable_to: 'document', usable_by_me: true })
      .then((r) => setMetaList((r.results ?? []).map((m) => ({ id: m.id, name: m.name }))))
      .catch(() => setMetaList([]))
    getWorkflowTemplates({})
      .then((r) =>
        setWfList(
          (r.results ?? [])
            .filter((w) => w.is_published)
            .map((w) => ({ id: w.id, name: w.name })),
        ),
      )
      .catch(() => setWfList([]))
  }, [open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('Nome obbligatorio.')
      return
    }
    setSaving(true)
    setError('')
    const allowed = allowedExt
      .split(/[,\s]+/)
      .map((s) => s.replace(/^\./, '').trim().toLowerCase())
      .filter(Boolean)
    const payload: Record<string, unknown> = {
      name: name.trim(),
      description: description.trim(),
      default_folder: defaultFolder || null,
      default_metadata_structure: defaultMeta || null,
      default_workflow_template: defaultWorkflow || null,
      auto_start_workflow: autoStart,
      default_status: defaultStatus,
      is_active: isActive,
      allowed_file_types: allowed,
      max_file_size_mb: maxMb.trim() ? parseInt(maxMb, 10) : null,
      default_metadata_values: {},
    }
    try {
      if (initial) await updateTemplate(initial.id, payload)
      else await createTemplate(payload)
      onSaved()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore salvataggio')
    } finally {
      setSaving(false)
    }
  }

  const modalRef = useFocusTrap(open)
  const onCloseCb = useCallback(() => onClose(), [onClose])
  useModalEscape(open, onCloseCb)

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
        aria-labelledby="modal-title-template-form"
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg bg-white shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 id="modal-title-template-form" className="text-lg font-semibold text-slate-800">
            {initial ? 'Modifica template' : 'Nuovo template'}
          </h2>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3 p-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Nome *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Descrizione</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              rows={2}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Cartella predefinita</label>
            <select
              value={defaultFolder}
              onChange={(e) => setDefaultFolder(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">— Nessuna —</option>
              {folders.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Struttura metadati</label>
            <select
              value={defaultMeta}
              onChange={(e) => setDefaultMeta(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">— Nessuna —</option>
              {metaList.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Workflow (pubblicato)</label>
            <select
              value={defaultWorkflow}
              onChange={(e) => setDefaultWorkflow(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">— Nessuno —</option>
              {wfList.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Stato iniziale</label>
            <select
              value={defaultStatus}
              onChange={(e) => setDefaultStatus(e.target.value as 'DRAFT' | 'IN_REVIEW')}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="DRAFT">Bozza</option>
              <option value="IN_REVIEW">In revisione</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={autoStart} onChange={(e) => setAutoStart(e.target.checked)} />
            Avvia workflow automaticamente dopo il caricamento
          </label>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Estensioni ammesse (es. pdf, docx)</label>
            <input
              value={allowedExt}
              onChange={(e) => setAllowedExt(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              placeholder="Vuoto = tutte"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Dimensione max (MB)</label>
            <input
              type="number"
              min={1}
              value={maxMb}
              onChange={(e) => setMaxMb(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              placeholder="Vuoto = nessun limite"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Attivo
          </label>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? 'Salvataggio...' : 'Salva'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
