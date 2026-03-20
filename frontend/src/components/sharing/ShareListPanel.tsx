import type { ShareLinkItem } from '../../services/sharingService'

interface ShareListPanelProps {
  shares: ShareLinkItem[]
  onRevoke: (shareId: string) => void
  onNewShare: () => void
  loading?: boolean
}

function formatDate(s: string | null): string {
  if (!s) return '—'
  try {
    return new Date(s).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return s
  }
}

export function ShareListPanel({ shares, onRevoke, onNewShare, loading }: ShareListPanelProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-slate-700">Condivisioni attive</h4>
        <button
          type="button"
          onClick={onNewShare}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700"
        >
          + Nuova condivisione
        </button>
      </div>
      {loading ? (
        <p className="text-sm text-slate-500">Caricamento...</p>
      ) : shares.length === 0 ? (
        <p className="text-sm text-slate-500">Nessuna condivisione.</p>
      ) : (
        <ul className="space-y-2">
          {shares.map((s) => (
            <li
              key={s.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-200 bg-slate-50/50 px-3 py-2 text-sm"
            >
              <div className="min-w-0 flex-1">
                <span className="font-medium text-slate-700">{s.recipient_display}</span>
                <span className="ml-2 text-slate-500">
                  {s.recipient_type === 'internal' ? 'Interno' : 'Esterno'}
                </span>
                {!s.is_valid && (
                  <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800">
                    {!s.is_active ? 'Revocato' : 'Scaduto'}
                  </span>
                )}
                <div className="mt-0.5 text-xs text-slate-500">
                  Scadenza: {s.expires_at ? formatDate(s.expires_at) : 'Nessuna'} · Accessi:{' '}
                  {s.access_count}
                  {s.max_accesses != null ? `/${s.max_accesses}` : ' (illimitato)'}
                </div>
              </div>
              {s.is_active && s.is_valid && (
                <button
                  type="button"
                  onClick={() => onRevoke(s.id)}
                  className="rounded bg-red-100 px-2 py-1 text-xs text-red-700 hover:bg-red-200"
                >
                  Revoca
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
