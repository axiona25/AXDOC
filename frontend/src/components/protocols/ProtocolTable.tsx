import type { ProtocolItem } from '../../services/protocolService'
import type { SignatureBadgeStatus } from '../../pages/ProtocolsPage'

interface ProtocolTableProps {
  protocols: ProtocolItem[]
  signatureStatusMap?: Record<string, SignatureBadgeStatus>
  directionFilter: string
  onDirectionFilterChange: (v: string) => void
  searchQuery: string
  onSearchChange: (v: string) => void
  onView: (p: ProtocolItem) => void
  onDownload: (p: ProtocolItem) => void
  onArchive: (p: ProtocolItem) => void
  onAddToDossier?: (p: ProtocolItem) => void
  onShare?: (p: ProtocolItem) => void
}

const SIGNATURE_BADGE: Record<string, { label: string; className: string }> = {
  pending: { label: 'Firma', className: 'bg-amber-100 text-amber-800' },
  completed: { label: 'Firmato', className: 'bg-green-100 text-green-800' },
  rejected: { label: 'Rifiutato', className: 'bg-red-100 text-red-800' },
  null: { label: '—', className: 'bg-slate-100 text-slate-500' },
}

export function ProtocolTable({
  protocols,
  signatureStatusMap = {},
  directionFilter,
  onDirectionFilterChange,
  searchQuery,
  onSearchChange,
  onView,
  onDownload,
  onArchive,
  onAddToDossier,
  onShare,
}: ProtocolTableProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={directionFilter}
          onChange={(e) => onDirectionFilterChange(e.target.value)}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700"
          aria-label="Filtro direzione"
        >
          <option value="">Tutti</option>
          <option value="in">In entrata</option>
          <option value="out">In uscita</option>
        </select>
        <input
          type="search"
          placeholder="Cerca per oggetto, mittente/destinatario, ID..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="min-w-[200px] rounded border border-slate-300 px-3 py-1.5 text-sm"
          aria-label="Ricerca"
        />
      </div>
      <div className="overflow-auto rounded border border-slate-200">
        <table className="w-full min-w-[800px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="px-3 py-2 text-left font-medium text-slate-700">ID Protocollo</th>
              <th className="px-3 py-2 text-left font-medium text-slate-700">Oggetto</th>
              <th className="px-3 py-2 text-left font-medium text-slate-700">Tipologia</th>
              <th className="px-3 py-2 text-left font-medium text-slate-700">Mittente/Dest.</th>
              <th className="px-3 py-2 text-left font-medium text-slate-700">UO</th>
              <th className="px-3 py-2 text-left font-medium text-slate-700">Data e ora</th>
              <th className="px-3 py-2 text-left font-medium text-slate-700">Categoria</th>
              <th className="px-3 py-2 text-left font-medium text-slate-700">Stato</th>
              <th className="px-3 py-2 text-left font-medium text-slate-700">Firma</th>
              <th className="px-3 py-2 text-right font-medium text-slate-700">Azioni</th>
            </tr>
          </thead>
          <tbody>
            {protocols.map((p) => (
              <tr
                key={p.id}
                className="border-b border-slate-100 hover:bg-slate-50"
                onDoubleClick={() => onView(p)}
              >
                <td className="px-3 py-2 font-mono text-slate-700">{p.protocol_display || p.protocol_id}</td>
                <td className="max-w-[200px] truncate px-3 py-2 text-slate-800" title={p.subject}>{p.subject || '—'}</td>
                <td className="px-3 py-2">
                  <span
                    className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${
                      p.direction === 'in' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {p.direction === 'in' ? 'IN' : 'OUT'}
                  </span>
                </td>
                <td className="max-w-[150px] truncate px-3 py-2 text-slate-600" title={p.sender_receiver}>{p.sender_receiver || '—'}</td>
                <td className="px-3 py-2 text-slate-600">{p.organizational_unit_name || '—'}</td>
                <td className="px-3 py-2 text-slate-600">
                  {p.registered_at ? (
                    <div>
                      <span>{new Date(p.registered_at).toLocaleDateString('it-IT')}</span>
                      <span className="ml-1 text-slate-400">
                        {new Date(p.registered_at).toLocaleTimeString('it-IT', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                  ) : (
                    '—'
                  )}
                </td>
                <td className="px-3 py-2">
                  <span className="inline-flex rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {p.category === 'email' ? 'Email' : p.category === 'pec' ? 'PEC' : p.category === 'other' ? 'Altro' : 'File'}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <span
                    className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${
                      p.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-400'
                    }`}
                  >
                    {p.status === 'archived' ? 'Archiviato' : 'Attivo'}
                  </span>
                </td>
                <td className="px-3 py-2">
                  {(() => {
                    const st: SignatureBadgeStatus = signatureStatusMap[p.id] ?? null
                    const key = st === null ? 'null' : st
                    const b = SIGNATURE_BADGE[key]
                    return b ? <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${b.className}`}>{b.label}</span> : null
                  })()}
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-1">
                    <button
                      type="button"
                      onClick={() => onView(p)}
                      className="rounded px-2 py-1 text-indigo-600 hover:bg-indigo-50"
                    >
                      Visualizza
                    </button>
                    <button
                      type="button"
                      onClick={() => (p.document ? onDownload(p) : alert('Nessun documento allegato a questo protocollo.'))}
                      className={`rounded px-2 py-1 ${p.document ? 'text-slate-600 hover:bg-slate-100' : 'cursor-not-allowed text-slate-300'}`}
                      title={p.document ? 'Scarica documento' : 'Nessun documento allegato'}
                    >
                      Download
                    </button>
                    {p.status === 'active' && (
                      <button
                        type="button"
                        onClick={() => onArchive(p)}
                        className="rounded px-2 py-1 text-amber-600 hover:bg-amber-50"
                      >
                        Archivia
                      </button>
                    )}
                    {onAddToDossier && (
                      <button
                        type="button"
                        onClick={() => onAddToDossier(p)}
                        className="rounded px-2 py-1 text-slate-600 hover:bg-slate-100"
                      >
                        A fascicolo
                      </button>
                    )}
                    {onShare && (
                      <button
                        type="button"
                        onClick={() => onShare(p)}
                        className="rounded px-2 py-1 text-indigo-600 hover:bg-indigo-50"
                      >
                        Condividi
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {protocols.length === 0 && (
        <p className="py-8 text-center text-slate-500">Nessun protocollo trovato.</p>
      )}
    </div>
  )
}
