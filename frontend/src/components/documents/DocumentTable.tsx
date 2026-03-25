import { memo, useCallback } from 'react'
import type { DocumentItem } from '../../services/documentService'
import { useAuthStore } from '../../store/authStore'
import { OCRStatusBadge } from './OCRStatusBadge'

const STATUS_STYLES: Record<string, string> = {
  DRAFT: 'bg-slate-200 text-slate-700 dark:bg-slate-600 dark:text-slate-100',
  IN_REVIEW: 'bg-orange-200 text-orange-800 dark:bg-orange-900/50 dark:text-orange-200',
  APPROVED: 'bg-green-200 text-green-800 dark:bg-green-900/50 dark:text-green-200',
  REJECTED: 'bg-red-200 text-red-800 dark:bg-red-900/50 dark:text-red-200',
  ARCHIVED: 'bg-slate-700 text-white dark:bg-slate-600',
}

interface DocumentTableRowProps {
  doc: DocumentItem
  isSelected: boolean
  showCheckbox: boolean
  onToggleSelect: (id: string) => void
  onOpen: (d: DocumentItem) => void
  onDownload: (d: DocumentItem) => void
  onView?: (d: DocumentItem) => void
  onNewVersion?: (d: DocumentItem) => void
  onCopy?: (d: DocumentItem) => void
  onMove?: (d: DocumentItem) => void
  onDelete?: (d: DocumentItem) => void
  canNewVersion: boolean
  canDelete: boolean
}

const DocumentTableRow = memo(function DocumentTableRow({
  doc,
  isSelected,
  showCheckbox,
  onToggleSelect,
  onOpen,
  onDownload,
  onView,
  onNewVersion,
  onCopy,
  onMove,
  onDelete,
  canNewVersion,
  canDelete,
}: DocumentTableRowProps) {
  return (
    <tr
      className="group cursor-pointer border-b border-slate-100 transition-colors hover:bg-indigo-50/50 dark:border-slate-700 dark:hover:bg-indigo-950/30"
      onDoubleClick={() => (onView ?? onOpen)(doc)}
    >
      {showCheckbox && (
        <td className="px-2 py-2">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggleSelect(doc.id)}
            onClick={(e) => e.stopPropagation()}
            aria-label={`Seleziona ${doc.title}`}
          />
        </td>
      )}
      <td className="max-w-[200px] truncate px-3 py-2 font-medium text-slate-800 dark:text-slate-100" title={doc.title}>
        {doc.locked_by && (
          <span className="mr-1" title="Bloccato">
            🔒
          </span>
        )}
        {doc.title}
      </td>
      <td className="px-3 py-2 text-slate-600 dark:text-slate-300">—</td>
      <td className="px-3 py-2 text-slate-600 dark:text-slate-300">—</td>
      <td className="px-3 py-2 text-slate-600 dark:text-slate-300">v{doc.current_version}</td>
      <td className="max-w-[140px] px-2 py-2">
        <OCRStatusBadge status={doc.ocr_status} confidence={doc.ocr_confidence} compact />
      </td>
      <td className="px-3 py-2">
        <span
          className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[doc.status] ?? 'bg-slate-200 text-slate-700 dark:bg-slate-600 dark:text-slate-100'}`}
        >
          {doc.status}
        </span>
      </td>
      <td className="px-3 py-2 text-slate-600 dark:text-slate-300">
        {doc.updated_at ? new Date(doc.updated_at).toLocaleDateString('it-IT') : '—'}
      </td>
      <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{doc.created_by_email ?? '—'}</td>
      <td className="px-3 py-2 text-right">
        <div className="flex justify-end gap-1">
          <button
            type="button"
            onClick={() => onDownload(doc)}
            className="rounded px-2 py-1 text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-950/50"
            title="Scarica"
          >
            ⬇
          </button>
          {onView && (
            <button
              type="button"
              onClick={() => onView(doc)}
              className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
              title="Visualizza"
            >
              📄
            </button>
          )}
          {onOpen && (
            <button
              type="button"
              onClick={() => onOpen(doc)}
              className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
              title="Dettaglio"
            >
              👁
            </button>
          )}
          {onNewVersion && canNewVersion && (
            <button
              type="button"
              onClick={() => onNewVersion(doc)}
              className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
              title="Nuova versione"
            >
              📤
            </button>
          )}
          {onCopy && (
            <button
              type="button"
              onClick={() => onCopy(doc)}
              className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
              title="Copia"
            >
              📋
            </button>
          )}
          {onMove && (
            <button
              type="button"
              onClick={() => onMove(doc)}
              className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
              title="Sposta"
            >
              📁
            </button>
          )}
          {onDelete && canDelete && (
            <button
              type="button"
              onClick={() => onDelete(doc)}
              className="rounded px-2 py-1 text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40"
              title="Elimina"
            >
              🗑
            </button>
          )}
        </div>
      </td>
    </tr>
  )
})

interface DocumentTableProps {
  documents: DocumentItem[]
  onOpen: (doc: DocumentItem) => void
  onDownload: (doc: DocumentItem) => void
  onView?: (doc: DocumentItem) => void
  onNewVersion?: (doc: DocumentItem) => void
  onCopy?: (doc: DocumentItem) => void
  onMove?: (doc: DocumentItem) => void
  onDelete?: (doc: DocumentItem) => void
  selectedIds?: Set<string>
  onSelectionChange?: (ids: Set<string>) => void
}

export function DocumentTable({
  documents,
  onOpen,
  onDownload,
  onView,
  onNewVersion,
  onCopy,
  onMove,
  onDelete,
  selectedIds = new Set(),
  onSelectionChange,
}: DocumentTableProps) {
  const user = useAuthStore((s) => s.user)

  const toggleSelect = useCallback(
    (id: string) => {
      if (!onSelectionChange) return
      const next = new Set(selectedIds)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      onSelectionChange(next)
    },
    [onSelectionChange, selectedIds],
  )

  const showCheckbox = !!onSelectionChange

  return (
    <div className="overflow-auto">
      <table className="w-full min-w-[600px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800">
            {showCheckbox && (
              <th className="w-8 px-2 py-2 text-left">
                <input
                  type="checkbox"
                  checked={selectedIds.size === documents.length && documents.length > 0}
                  onChange={(e) => {
                    if (e.target.checked) onSelectionChange!(new Set(documents.map((d) => d.id)))
                    else onSelectionChange!(new Set())
                  }}
                  aria-label="Seleziona tutti"
                />
              </th>
            )}
            <th className="px-3 py-2 text-left font-medium text-slate-700 dark:text-slate-200">Nome</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700 dark:text-slate-200">Tipo</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700 dark:text-slate-200">Dimensione</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700 dark:text-slate-200">Versione</th>
            <th className="px-2 py-2 text-left font-medium text-slate-700 dark:text-slate-200">OCR</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700 dark:text-slate-200">Stato</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700 dark:text-slate-200">Modifica</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700 dark:text-slate-200">Autore</th>
            <th className="px-3 py-2 text-right font-medium text-slate-700 dark:text-slate-200">Azioni</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <DocumentTableRow
              key={doc.id}
              doc={doc}
              isSelected={selectedIds.has(doc.id)}
              showCheckbox={showCheckbox}
              onToggleSelect={toggleSelect}
              onOpen={onOpen}
              onDownload={onDownload}
              onView={onView}
              onNewVersion={onNewVersion}
              onCopy={onCopy}
              onMove={onMove}
              onDelete={onDelete}
              canNewVersion={doc.can_write !== false || user?.role === 'ADMIN'}
              canDelete={doc.can_delete !== false || user?.role === 'ADMIN'}
            />
          ))}
        </tbody>
      </table>
      {documents.length === 0 && (
        <div className="py-8 text-center text-slate-500 dark:text-slate-400">Nessun documento in questa cartella.</div>
      )}
    </div>
  )
}
