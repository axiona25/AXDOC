import { useState, useCallback } from 'react'
import type { FolderItem } from '../../services/documentService'
import type { MetadataStructure, MetadataValues } from '../../types/metadata'
import { DynamicMetadataForm } from '../metadata/DynamicMetadataForm'

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
  }) => Promise<void>
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
  }, [defaultFolderId])

  const handleClose = () => {
    if (!uploading) {
      reset()
      onClose()
    }
  }

  const validate = (): boolean => {
    if (!file) {
      setError('Seleziona un file.')
      return false
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`Il file non deve superare ${MAX_SIZE_MB} MB.`)
      return false
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
      await onUpload({
        title: title.trim() || file.name,
        description: description.trim(),
        folderId,
        file,
        metadataStructureId: metadataStructureId || undefined,
        metadataValues: Object.keys(metadataValues).length ? metadataValues : undefined,
        ...(showVisibility && { visibility }),
      })
      handleClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload fallito.')
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }

  const handleFileChange = (f: File | null) => {
    setFile(f)
    if (f && !title) setTitle(f.name)
    setError('')
  }

  const displayProgress = externalProgress ?? progress

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-lg font-semibold text-slate-800">Carica documento</h2>
          <button
            type="button"
            onClick={handleClose}
            disabled={uploading}
            className="rounded p-1 text-slate-500 hover:bg-slate-100 disabled:opacity-50"
            aria-label="Chiudi"
          >
            ✕
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-4">
          <div
            className={`mb-4 rounded-lg border-2 border-dashed p-6 text-center ${dragOver ? 'border-indigo-400 bg-indigo-50' : 'border-slate-200'}`}
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
                <p className="text-sm font-medium text-slate-700">{file.name} ({(file.size / 1024).toFixed(1)} KB)</p>
              ) : (
                <p className="text-sm text-slate-500">Trascina un file qui o clicca per selezionare</p>
              )}
            </label>
          </div>
          <div className="mb-3">
            <label htmlFor="upload-title" className="mb-1 block text-sm font-medium text-slate-700">Titolo</label>
            <input
              id="upload-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              placeholder="Titolo documento"
              maxLength={500}
            />
          </div>
          <div className="mb-3">
            <label htmlFor="upload-desc" className="mb-1 block text-sm font-medium text-slate-700">Descrizione</label>
            <textarea
              id="upload-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              placeholder="Opzionale"
              rows={2}
            />
          </div>
          <div className="mb-4">
            <label htmlFor="upload-folder" className="mb-1 block text-sm font-medium text-slate-700">Cartella</label>
            <select
              id="upload-folder"
              value={folderId ?? ''}
              onChange={(e) => setFolderId(e.target.value || null)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">— Root —</option>
              {folders.map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          </div>
          {showVisibility && (
            <div className="mb-4">
              <label htmlFor="upload-visibility" className="mb-1 block text-sm font-medium text-slate-700">Visibilità</label>
              <select
                id="upload-visibility"
                value={visibility}
                onChange={(e) => setVisibility(e.target.value as 'personal' | 'office')}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="personal">Personale</option>
                <option value="office">Ufficio</option>
              </select>
            </div>
          )}
          {metadataStructures.length > 0 && (
            <>
              {!metadataStructureId && (
                <p className="mb-2 text-xs text-amber-700">Si consiglia di selezionare un tipo documento per i metadati AGID.</p>
              )}
              <div className="mb-3">
                <label htmlFor="upload-type" className="mb-1 block text-sm font-medium text-slate-700">Tipo documento</label>
                <select
                  id="upload-type"
                  value={metadataStructureId ?? ''}
                  onChange={(e) => {
                    setMetadataStructureId(e.target.value || null)
                    setMetadataValues({})
                    setMetadataErrors({})
                  }}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
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
                    <span className="mb-2 block text-sm font-medium text-slate-700">Metadati</span>
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
            <div className="mb-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700">
              {error || externalError}
            </div>
          )}
          {uploading && (
            <div className="mb-3">
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full bg-indigo-600 transition-all duration-300"
                  style={{ width: `${displayProgress}%` }}
                />
              </div>
              <p className="mt-1 text-xs text-slate-500">{displayProgress}%</p>
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={uploading}
              className="rounded bg-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-300 disabled:opacity-50"
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={!file || uploading}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {uploading ? 'Caricamento...' : 'Carica'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
