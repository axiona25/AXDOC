import { Link } from 'react-router-dom'
import { FileSpreadsheet, FileText } from 'lucide-react'
import type { DossierItem } from '../../services/dossierService'
import type { SignatureBadgeStatus } from '../../pages/DossiersPage'

interface DossierListProps {
  dossiers: DossierItem[]
  signatureStatusMap?: Record<string, SignatureBadgeStatus>
  activeTab: 'mine' | 'all' | 'archived'
  onTabChange: (tab: 'mine' | 'all' | 'archived') => void
  onOpen: (d: DossierItem) => void
  onEdit?: (d: DossierItem) => void
  onArchive?: (d: DossierItem) => void
  onDelete?: (d: DossierItem) => void
  onExportExcel?: () => void
  onExportPdf?: () => void
}

const SIG_BADGE: Record<string, { label: string; className: string }> = {
  pending: { label: 'Firma', className: 'bg-amber-100 text-amber-800' },
  completed: { label: 'Firmato', className: 'bg-green-100 text-green-800' },
  rejected: { label: 'Rifiutato', className: 'bg-red-100 text-red-800' },
  null: { label: '', className: 'bg-slate-100 text-slate-500' },
}

export function DossierList({
  dossiers,
  signatureStatusMap = {},
  activeTab,
  onTabChange,
  onOpen,
  onEdit,
  onArchive,
  onDelete,
  onExportExcel,
  onExportPdf,
}: DossierListProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200">
        <button
          type="button"
          onClick={() => onTabChange('mine')}
          className={`border-b-2 px-3 py-2 text-sm font-medium ${
            activeTab === 'mine' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-600 hover:text-slate-800'
          }`}
        >
          I miei fascicoli
        </button>
        <button
          type="button"
          onClick={() => onTabChange('all')}
          className={`border-b-2 px-3 py-2 text-sm font-medium ${
            activeTab === 'all' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-600 hover:text-slate-800'
          }`}
        >
          Tutti i fascicoli
        </button>
        <button
          type="button"
          onClick={() => onTabChange('archived')}
          className={`border-b-2 px-3 py-2 text-sm font-medium ${
            activeTab === 'archived' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-600 hover:text-slate-800'
          }`}
        >
          Archiviati
        </button>
        {(onExportExcel || onExportPdf) && (
          <div className="ml-auto flex flex-wrap gap-2 pb-2">
            {onExportExcel && (
              <button
                type="button"
                onClick={onExportExcel}
                className="flex items-center gap-1.5 rounded bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
              >
                <FileSpreadsheet className="h-4 w-4" aria-hidden />
                Esporta Excel
              </button>
            )}
            {onExportPdf && (
              <button
                type="button"
                onClick={onExportPdf}
                className="flex items-center gap-1.5 rounded bg-slate-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
              >
                <FileText className="h-4 w-4" aria-hidden />
                Esporta PDF
              </button>
            )}
          </div>
        )}
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {dossiers.map((d) => (
          <div
            key={d.id}
            className="flex flex-col rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <Link to={`/dossiers/${d.id}`} className="font-mono text-sm text-indigo-600 hover:underline">{d.identifier}</Link>
                <h3 className="mt-1 truncate font-medium text-slate-800" title={d.title}>
                  <Link to={`/dossiers/${d.id}`} className="hover:text-indigo-600">{d.title}</Link>
                </h3>
                <p className="mt-1 text-xs text-slate-500">{d.responsible_email || '—'}</p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {(() => {
                  const st: SignatureBadgeStatus = signatureStatusMap[d.id] ?? null
                  const key = st === null ? 'null' : st
                  const b = SIG_BADGE[key]
                  return b?.label ? <span className={`rounded px-2 py-0.5 text-xs font-medium ${b.className}`}>{b.label}</span> : null
                })()}
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium ${
                    d.status === 'archived' ? 'bg-slate-200 text-slate-700' : 'bg-green-100 text-green-800'
                  }`}
                >
                  {d.status === 'archived' ? 'Archiviato' : 'Aperto'}
                </span>
              </div>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              {d.document_count} doc. · {d.protocol_count} prot.
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Aggiornato {d.updated_at ? new Date(d.updated_at).toLocaleDateString('it-IT') : '—'}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => onOpen(d)}
                className="rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
              >
                Apri
              </button>
              {onEdit && d.status !== 'archived' && (
                <button type="button" onClick={() => onEdit(d)} className="rounded bg-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-300">
                  Modifica
                </button>
              )}
              {onArchive && d.status !== 'archived' && (
                <button type="button" onClick={() => onArchive(d)} className="rounded bg-amber-100 px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-200">
                  Archivia
                </button>
              )}
              {onDelete && d.status === 'open' && (
                <button type="button" onClick={() => onDelete(d)} className="rounded bg-red-100 px-3 py-1.5 text-xs font-medium text-red-800 hover:bg-red-200">
                  Elimina
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      {dossiers.length === 0 && (
        <p className="py-8 text-center text-slate-500">Nessun fascicolo trovato.</p>
      )}
    </div>
  )
}
