import type { DocumentItem } from '../../services/documentService'
import { useAuthStore } from '../../store/authStore'

const STATUS_STYLES: Record<string, string> = {
  DRAFT: 'bg-slate-200 text-slate-700',
  IN_REVIEW: 'bg-orange-200 text-orange-800',
  APPROVED: 'bg-green-200 text-green-800',
  REJECTED: 'bg-red-200 text-red-800',
  ARCHIVED: 'bg-slate-700 text-white',
}

interface DocumentTableProps {
  documents: DocumentItem[]
  onOpen: (doc: DocumentItem) => void
  onDownload: (doc: DocumentItem) => void
  /** FASE 19: apre DocumentViewer (doppio click e pulsante Visualizza) */
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

  const toggleSelect = (id: string) => {
    if (!onSelectionChange) return
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onSelectionChange(next)
  }

  return (
    <div className="overflow-auto">
      <table className="w-full min-w-[600px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50">
            {onSelectionChange && (
              <th className="w-8 px-2 py-2 text-left">
                <input
                  type="checkbox"
                  checked={selectedIds.size === documents.length && documents.length > 0}
                  onChange={(e) => {
                    if (e.target.checked) onSelectionChange(new Set(documents.map((d) => d.id)))
                    else onSelectionChange(new Set())
                  }}
                  aria-label="Seleziona tutti"
                />
              </th>
            )}
            <th className="px-3 py-2 text-left font-medium text-slate-700">Nome</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">Tipo</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">Dimensione</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">Versione</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">Stato</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">Modifica</th>
            <th className="px-3 py-2 text-left font-medium text-slate-700">Autore</th>
            <th className="px-3 py-2 text-right font-medium text-slate-700">Azioni</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <tr
              key={doc.id}
              className="group border-b border-slate-100 hover:bg-indigo-50/50 cursor-pointer transition-colors"
              onDoubleClick={() => (onView ?? onOpen)(doc)}
            >
              {onSelectionChange && (
                <td className="px-2 py-2">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(doc.id)}
                    onChange={() => toggleSelect(doc.id)}
                    onClick={(e) => e.stopPropagation()}
                    aria-label={`Seleziona ${doc.title}`}
                  />
                </td>
              )}
              <td className="max-w-[200px] truncate px-3 py-2 font-medium text-slate-800" title={doc.title}>
                {doc.locked_by && (
                  <span className="mr-1" title="Bloccato">🔒</span>
                )}
                {doc.title}
              </td>
              <td className="px-3 py-2 text-slate-600">—</td>
              <td className="px-3 py-2 text-slate-600">—</td>
              <td className="px-3 py-2 text-slate-600">v{doc.current_version}</td>
              <td className="px-3 py-2">
                <span
                  className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[doc.status] ?? 'bg-slate-200 text-slate-700'}`}
                >
                  {doc.status}
                </span>
              </td>
              <td className="px-3 py-2 text-slate-600">
                {doc.updated_at ? new Date(doc.updated_at).toLocaleDateString('it-IT') : '—'}
              </td>
              <td className="px-3 py-2 text-slate-600">{doc.created_by_email ?? '—'}</td>
              <td className="px-3 py-2 text-right">
                <div className="flex justify-end gap-1">
                  <button
                    type="button"
                    onClick={() => onDownload(doc)}
                    className="rounded px-2 py-1 text-indigo-600 hover:bg-indigo-50"
                    title="Scarica"
                  >
                    ⬇
                  </button>
                  {onView && (
                    <button
                      type="button"
                      onClick={() => onView(doc)}
                      className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100"
                      title="Visualizza"
                    >
                      📄
                    </button>
                  )}
                  {onOpen && (
                    <button
                      type="button"
                      onClick={() => onOpen(doc)}
                      className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100"
                      title="Dettaglio"
                    >
                      👁
                    </button>
                  )}
                  {onNewVersion && (doc.can_write !== false || user?.role === 'ADMIN') && (
                    <button
                      type="button"
                      onClick={() => onNewVersion(doc)}
                      className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100"
                      title="Nuova versione"
                    >
                      📤
                    </button>
                  )}
                  {onCopy && (
                    <button
                      type="button"
                      onClick={() => onCopy(doc)}
                      className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100"
                      title="Copia"
                    >
                      📋
                    </button>
                  )}
                  {onMove && (
                    <button
                      type="button"
                      onClick={() => onMove(doc)}
                      className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100"
                      title="Sposta"
                    >
                      📁
                    </button>
                  )}
                  {onDelete && (doc.can_delete !== false || user?.role === 'ADMIN') && (
                    <button
                      type="button"
                      onClick={() => onDelete(doc)}
                      className="rounded px-2 py-1 text-red-600 hover:bg-red-50"
                      title="Elimina"
                    >
                      🗑
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {documents.length === 0 && (
        <div className="py-8 text-center text-slate-500">Nessun documento in questa cartella.</div>
      )}
    </div>
  )
}
