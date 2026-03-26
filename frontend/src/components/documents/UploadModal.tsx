import { useState, useCallback, useEffect, useRef } from 'react'
import { announce } from '../common/ScreenReaderAnnouncer'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useModalEscape } from '../../hooks/useModalAccessibility'
import type { DocumentItem, FolderItem } from '../../services/documentService'
import { getDocument } from '../../services/documentService'
import type { MetadataStructure, MetadataValues } from '../../types/metadata'
import { DynamicMetadataForm } from '../metadata/DynamicMetadataForm'
import { compressImage } from '../../utils/imageCompressor'
import { getTemplateList } from '../../services/templateService'
import type { DocumentTemplate } from '../../services/templateService'
import { OCRStatusBadge } from './OCRStatusBadge'
import { ClassificationSuggestions } from './ClassificationSuggestions'

const MAX_SIZE_MB = 200

interface UploadModalProps {
  open: boolean
  onClose: () => void
  onUpload: (data: {
    title: string
    description: string
    folderId: string | null
    file: File
    metadataStructureId?: string | null
    metadataValues?: MetadataValues
    /** FASE 19: per sezione "I miei File" */
    visibility?: 'personal' | 'office'
    /** FASE 26: avvio workflow post-upload */
    templateMeta?: { auto_start_workflow: boolean; workflowTemplateId: string | null } | null
  }) => Promise<DocumentItem | void>
  folders: FolderItem[]
  defaultFolderId?: string | null
  progress?: number
  error?: string
  metadataStructures?: MetadataStructure[]
  /** FASE 19: mostra campo Visibilità (Personale/Ufficio) */
  showVisibility?: boolean
}

export function UploadModal({
  open,
  onClose,
  onUpload,
  folders,
  defaultFolderId,
  progress: externalProgress,
  error: externalError,
  metadataStructures = [],
  showVisibility = false,
}: UploadModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [folderId, setFolderId] = useState<string | null>(defaultFolderId ?? null)
  const [file, setFile] = useState<File | null>(null)
  const [visibility, setVisibility] = useState<'personal' | 'office'>('personal')
  const [metadataStructureId, setMetadataStructureId] = useState<string | null>(null)
  const [metadataValues, setMetadataValues] = useState<MetadataValues>({})
  const [metadataErrors, setMetadataErrors] = useState<Record<string, string>>({})
  const [dragOver, setDragOver] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [compressing, setCompressing] = useState(false)
  const [templates, setTemplates] = useState<DocumentTemplate[]>([])
  const [templateId, setTemplateId] = useState<string | null>(null)
  const [phase, setPhase] = useState<'form' | 'followup'>('form')
  const [followupDoc, setFollowupDoc] = useState<DocumentItem | null>(null)
  const pollCancel = useRef(false)

  useEffect(() => {
    if (open) {
      getTemplateList().then(setTemplates).catch(() => setTemplates([]))
    }
  }, [open])

  const reset = useCallback(() => {
    setTitle('')
    setDescription('')
    setFolderId(defaultFolderId ?? null)
    setFile(null)
    setVisibility('personal')
    setMetadataStructureId(null)
    setMetadataValues({})
    setMetadataErrors({})
    setProgress(0)
    setError('')
    setUploading(false)
    setCompressing(false)
    setTemplateId(null)
    setPhase('form')
    setFollowupDoc(null)
    pollCancel.current = false
  }, [defaultFolderId])

  const handleClose = useCallback(() => {
    if (!uploading && !compressing) {
      reset()
      onClose()
    }
  }, [uploading, compressing, reset, onClose])

  const modalRef = useFocusTrap(open)
  useModalEscape(open, handleClose)

  const selectedTemplate = templateId ? templates.find((t) => t.id === templateId) : null

  const validate = (): boolean => {
    if (!file) {
      setError('Seleziona un file.')
      return false
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`Il file non deve superare ${MAX_SIZE_MB} MB.`)
      return false
    }
    if (selectedTemplate?.max_file_size_mb != null) {
      const maxBytes = selectedTemplate.max_file_size_mb * 1024 * 1024
      if (file.size > maxBytes) {
        setError(`Il file supera il limite del template (${selectedTemplate.max_file_size_mb} MB).`)
        return false
      }
    }
    if (selectedTemplate?.allowed_file_types?.length) {
      const ext = (file.name.split('.').pop() || '').toLowerCase()
      const allowed = selectedTemplate.allowed_file_types.map((x) => x.replace(/^\./, '').toLowerCase())
      if (!allowed.includes(ext)) {
        setError(`Estensione non ammessa dal template. Consentite: ${allowed.join(', ')}`)
        return false
      }
    }
    setError('')
    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !validate()) return
    setUploading(true)
    setError('')
    try {
      const meta =
        selectedTemplate?.auto_start_workflow && selectedTemplate.default_workflow_template
          ? {
              auto_start_workflow: true,
              workflowTemplateId: selectedTemplate.default_workflow_template,
            }
          : null
      const created = await onUpload({
        title: title.trim() || file.name,
        description: description.trim(),
        folderId,
        file,
        metadataStructureId: metadataStructureId || undefined,
        metadataValues: Object.keys(metadataValues).length ? metadataValues : undefined,
        ...(showVisibility && { visibility }),
        templateMeta: meta,
      })
      announce('Documento caricato con successo')
      if (created && typeof created === 'object' && 'id' in created && created.id) {
        setFollowupDoc(created as DocumentItem)
        setPhase('followup')
      } else {
        handleClose()
      }
    } catch (err) {
      announce('Errore nel caricamento del documento', 'assertive')
      setError(err instanceof Error ? err.message : 'Upload fallito.')
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }

  const handleFileChange = async (f: File | null) => {
    if (!f) {
      setFile(null)
      return
    }
    setError('')

    // Comprimi immagini automaticamente
    if (f.type.startsWith('image/') && f.type !== 'image/gif' && f.type !== 'image/svg+xml') {
      setCompressing(true)
      try {
        const compressed = await compressImage(f)
        setFile(compressed)
        if (!title) setTitle(compressed.name)
      } catch {
        setFile(f)
        if (!title) setTitle(f.name)
      } finally {
        setCompressing(false)
      }
    } else {
      setFile(f)
      if (!title) setTitle(f.name)
    }
  }

  const displayProgress = externalProgress ?? progress

  useEffect(() => {
    if (phase !== 'followup' || !followupDoc?.id) return
    const docId = followupDoc.id
    pollCancel.current = false
    let attempts = 0
    const maxAttempts = 60

    const poll = () => {
      if (pollCancel.current) return
      getDocument(docId)
        .then((d) => {
          if (pollCancel.current) return
          setFollowupDoc(d)
          attempts += 1
          const s = d.ocr_status
          const terminal =
            s === 'completed' || s === 'failed' || s === 'not_needed' || attempts >= maxAttempts
          if (!terminal) {
            window.setTimeout(poll, 2000)
          }
        })
        .catch(() => {
          if (!pollCancel.current && attempts < maxAttempts) {
            attempts += 1
            window.setTimeout(poll, 3000)
          }
        })
    }
    poll()
    return () => {
      pollCancel.current = true
    }
  }, [phase, followupDoc?.id])

  const followupRefresh = useCallback(() => {
    if (!followupDoc?.id) return
    getDocument(followupDoc.id).then(setFollowupDoc).catch(() => {})
  }, [followupDoc?.id])

  const canAutoAnalyze =
    !!followupDoc &&
    (followupDoc.ocr_status === 'completed' || followupDoc.ocr_status === 'not_needed')

  const aiHintFile =
    file &&
    (file.type === 'application/pdf' ||
      file.type.startsWith('image/') ||
      /\.(pdf|png|jpe?g|tiff?|webp|bmp)$/i.test(file.name))

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) handleClose()
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title-upload"
        className={`w-full rounded-lg border border-slate-200 bg-white shadow-xl dark:border-slate-600 dark:bg-slate-800 ${
          phase === 'followup' ? 'max-w-2xl' : 'max-w-lg'
        }`}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-600">
          <h2 id="modal-title-upload" className="text-lg font-semibold text-slate-800 dark:text-slate-100">
            {phase === 'followup' ? 'Documento caricato' : 'Carica documento'}
          </h2>
          <button
            type="button"
            onClick={handleClose}
            disabled={uploading || compressing}
            className="rounded p-1 text-slate-500 hover:bg-slate-100 disabled:opacity-50 dark:text-slate-400 dark:hover:bg-slate-700"
            aria-label="Chiudi"
          >
            ✕
          </button>
        </div>
        {phase === 'followup' && followupDoc ? (
          <div className="space-y-4 p-4">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              L&apos;estrazione del testo (OCR o PDF nativo) può richiedere alcuni secondi. Puoi chiudere e
              aprire il documento dal dettaglio in qualsiasi momento.
            </p>
            <div>
              <span className="mb-1 block text-xs font-medium uppercase text-slate-500 dark:text-slate-400">
                Stato testo
              </span>
              <OCRStatusBadge
                status={followupDoc.ocr_status}
                confidence={followupDoc.ocr_confidence}
                error={followupDoc.ocr_error}
                compact
              />
            </div>
            <ClassificationSuggestions
              key={`${followupDoc.id}-ai`}
              document={followupDoc}
              onRefresh={followupRefresh}
              compact
              autoAnalyze={canAutoAnalyze}
            />
            <div className="flex justify-end border-t border-slate-200 pt-4 dark:border-slate-600">
              <button
                type="button"
                onClick={handleClose}
                className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 dark:hover:bg-indigo-500"
              >
                Chiudi
              </button>
            </div>
          </div>
        ) : (
        <form onSubmit={handleSubmit} className="p-4">
          {templates.length > 0 && (
            <div className="mb-4">
              <label htmlFor="upload-template" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Usa template (opzionale)
              </label>
              <select
                id="upload-template"
                value={templateId ?? ''}
                onChange={(e) => {
                  const id = e.target.value || null
                  setTemplateId(id)
                  const tpl = id ? templates.find((t) => t.id === id) : null
                  if (tpl) {
                    if (tpl.default_folder) setFolderId(tpl.default_folder)
                    if (tpl.default_metadata_structure) {
                      setMetadataStructureId(tpl.default_metadata_structure)
                      const dv = tpl.default_metadata_values as MetadataValues
                      setMetadataValues(dv && typeof dv === 'object' ? { ...dv } : {})
                    }
                  }
                }}
                className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
              >
                <option value="">— Nessuno —</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
              {selectedTemplate?.auto_start_workflow && selectedTemplate.default_workflow_template_name && (
                <p className="mt-1 text-xs text-indigo-700 dark:text-indigo-300">
                  Dopo il caricamento verrà avviato il workflow: {selectedTemplate.default_workflow_template_name}
                </p>
              )}
            </div>
          )}
          <div
            className={`mb-4 rounded-lg border-2 border-dashed p-6 text-center ${
              dragOver
                ? 'border-indigo-400 bg-indigo-50 dark:border-indigo-500 dark:bg-indigo-950/30'
                : 'border-slate-200 dark:border-slate-600'
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              const f = e.dataTransfer.files[0]
              if (f) handleFileChange(f)
            }}
          >
            <input
              type="file"
              className="hidden"
              id="upload-file"
              onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
            />
            <label htmlFor="upload-file" className="cursor-pointer">
              {file ? (
                <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                  {file.name} ({(file.size / 1024).toFixed(1)} KB)
                </p>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">Trascina un file qui o clicca per selezionare</p>
              )}
            </label>
            {compressing && (
              <p className="mt-2 text-xs text-indigo-600 dark:text-indigo-400">⏳ Compressione immagine in corso...</p>
            )}
            {aiHintFile && (
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                Dopo il caricamento potrai usare l&apos;analisi AI sui suggerimenti di classificazione e metadati, in
                base al testo estratto.
              </p>
            )}
          </div>
          <div className="mb-3">
            <label htmlFor="upload-title" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Titolo
            </label>
            <input
              id="upload-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
              placeholder="Titolo documento"
              maxLength={500}
            />
          </div>
          <div className="mb-3">
            <label htmlFor="upload-desc" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Descrizione
            </label>
            <textarea
              id="upload-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
              placeholder="Opzionale"
              rows={2}
            />
          </div>
          <div className="mb-4">
            <label htmlFor="upload-folder" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Cartella
            </label>
            <select
              id="upload-folder"
              value={folderId ?? ''}
              onChange={(e) => setFolderId(e.target.value || null)}
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
            >
              <option value="">— Root —</option>
              {folders.map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          </div>
          {showVisibility && (
            <div className="mb-4">
              <label htmlFor="upload-visibility" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                Visibilità
              </label>
              <select
                id="upload-visibility"
                value={visibility}
                onChange={(e) => setVisibility(e.target.value as 'personal' | 'office')}
                className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
              >
                <option value="personal">Personale</option>
                <option value="office">Ufficio</option>
              </select>
            </div>
          )}
          {metadataStructures.length > 0 && (
            <>
              {!metadataStructureId && (
                <p className="mb-2 text-xs text-amber-700 dark:text-amber-300">
                  Si consiglia di selezionare un tipo documento per i metadati AGID.
                </p>
              )}
              <div className="mb-3">
                <label htmlFor="upload-type" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Tipo documento
                </label>
                <select
                  id="upload-type"
                  value={metadataStructureId ?? ''}
                  onChange={(e) => {
                    setMetadataStructureId(e.target.value || null)
                    setMetadataValues({})
                    setMetadataErrors({})
                  }}
                  className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
                >
                  <option value="">— Nessuno —</option>
                  {metadataStructures.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
              {metadataStructureId && (() => {
                const structure = metadataStructures.find((s) => s.id === metadataStructureId)
                return structure ? (
                  <div className="mb-4">
                    <span className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">Metadati</span>
                    <DynamicMetadataForm
                      structure={structure}
                      values={metadataValues}
                      onChange={setMetadataValues}
                      errors={metadataErrors}
                    />
                  </div>
                ) : null
              })()}
            </>
          )}
          {(error || externalError) && (
            <div className="mb-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
              {error || externalError}
            </div>
          )}
          {uploading && (
            <div className="mb-3">
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-600">
                <div
                  className="h-full bg-indigo-600 transition-all duration-300 dark:bg-indigo-500"
                  style={{ width: `${displayProgress}%` }}
                />
              </div>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{displayProgress}%</p>
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={uploading || compressing}
              className="rounded bg-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-300 disabled:opacity-50 dark:bg-slate-600 dark:text-slate-100 dark:hover:bg-slate-500"
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={!file || uploading || compressing}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 dark:hover:bg-indigo-500"
            >
              {uploading ? 'Caricamento...' : 'Carica'}
            </button>
          </div>
        </form>
        )}
      </div>
    </div>
  )
}
