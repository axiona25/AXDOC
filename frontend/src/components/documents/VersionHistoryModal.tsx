import type { DocumentVersionItem } from '../../services/documentService'
import { downloadDocument } from '../../services/documentService'

interface VersionHistoryModalProps {
  open: boolean
  onClose: () => void
  documentId: string
  title: string
  versions: DocumentVersionItem[]
}

export function VersionHistoryModal({
  open,
  onClose,
  documentId,
  title,
  versions,
}: VersionHistoryModalProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-lg font-semibold text-slate-800">Storico versioni — {title}</h2>
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
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left">
                <th className="pb-2 font-medium text-slate-700">Versione</th>
                <th className="pb-2 font-medium text-slate-700">File</th>
                <th className="pb-2 font-medium text-slate-700">Data</th>
                <th className="pb-2 font-medium text-slate-700">Modifica</th>
                <th className="pb-2 text-right font-medium text-slate-700">Azioni</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id} className="border-b border-slate-100">
                  <td className="py-2">
                    <span className={v.is_current ? 'font-semibold text-indigo-600' : ''}>
                      v{v.version_number}
                      {v.is_current && ' (corrente)'}
                    </span>
                  </td>
                  <td className="py-2 text-slate-600">{v.file_name}</td>
                  <td className="py-2 text-slate-600">
                    {v.created_at ? new Date(v.created_at).toLocaleString('it-IT') : '—'}
                  </td>
                  <td className="max-w-[200px] truncate py-2 text-slate-600" title={v.change_description}>
                    {v.change_description || '—'}
                  </td>
                  <td className="py-2 text-right">
                    <button
                      type="button"
                      onClick={() => downloadDocument(documentId, v.version_number, v.file_name)}
                      className="rounded px-2 py-1 text-indigo-600 hover:bg-indigo-50"
                    >
                      Scarica
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
