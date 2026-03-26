import { useState, useEffect, useCallback } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useModalEscape } from '../../hooks/useModalAccessibility'
import { getStructureDocuments } from '../../services/metadataService'
import { DynamicMetadataForm } from './DynamicMetadataForm'
import type { MetadataStructure, MetadataValues } from '../../types/metadata'

interface MetadataPreviewModalProps {
  open: boolean
  onClose: () => void
  structure: MetadataStructure | null
}

export function MetadataPreviewModal({ open, onClose, structure }: MetadataPreviewModalProps) {
  const [documents, setDocuments] = useState<unknown[]>([])
  const [loading, setLoading] = useState(false)
  const [previewValues, setPreviewValues] = useState<MetadataValues>({})

  useEffect(() => {
    if (open && structure) {
      setPreviewValues({})
      setLoading(true)
      getStructureDocuments(structure.id)
        .then(setDocuments)
        .finally(() => setLoading(false))
    }
  }, [open, structure?.id])

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
        aria-labelledby="modal-title-metadata-preview"
        className="max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-lg bg-white shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 id="modal-title-metadata-preview" className="text-lg font-semibold text-slate-800">
            Anteprima — {structure?.name ?? ''}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-slate-500 hover:bg-slate-100"
            aria-label="Chiudi"
          >
            ✕
          </button>
        </div>
        <div className="overflow-auto p-4">
          <h3 className="mb-2 text-sm font-medium text-slate-700">Form metadati (preview)</h3>
          {structure && (
            <DynamicMetadataForm
              structure={structure}
              values={previewValues}
              onChange={setPreviewValues}
              readOnly={false}
            />
          )}
          <h3 className="mt-6 mb-2 text-sm font-medium text-slate-700">Documenti associati</h3>
          {loading ? (
            <p className="text-slate-500">Caricamento...</p>
          ) : (
            <ul className="list-inside list-disc text-sm text-slate-600">
              {(documents as Array<{ title?: string; id?: string }>).map((d) => (
                <li key={d.id ?? d.title}>{d.title ?? d.id ?? '—'}</li>
              ))}
              {(!documents || documents.length === 0) && <li>Nessun documento</li>}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
