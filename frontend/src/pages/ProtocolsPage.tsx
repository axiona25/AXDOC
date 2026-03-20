import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ProtocolTable } from '../components/protocols/ProtocolTable'
import { ProtocolFormModal } from '../components/protocols/ProtocolFormModal'
import { ShareModal } from '../components/sharing/ShareModal'
import type { ProtocolItem, CreateProtocolPayload } from '../services/protocolService'
import { getProtocols, archiveProtocol, downloadProtocolDocument } from '../services/protocolService'
import { shareProtocol } from '../services/sharingService'
import { getSignaturesByTarget } from '../services/signatureService'

export type SignatureBadgeStatus = 'pending' | 'completed' | 'rejected' | null

export function ProtocolsPage() {
  const navigate = useNavigate()
  const [protocols, setProtocols] = useState<ProtocolItem[]>([])
  const [signatureStatusMap, setSignatureStatusMap] = useState<Record<string, SignatureBadgeStatus>>({})
  const [directionFilter, setDirectionFilter] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [loading, setLoading] = useState(true)
  const [formOpen, setFormOpen] = useState(false)
  const [shareProtocolItem, setShareProtocolItem] = useState<ProtocolItem | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    const params: { direction?: 'in' | 'out'; search?: string; page?: number } = {}
    if (directionFilter === 'in' || directionFilter === 'out') params.direction = directionFilter
    if (searchQuery.trim()) params.search = searchQuery.trim()
    getProtocols(params)
      .then((res) => {
        setProtocols(res.results || [])
        return getSignaturesByTarget('protocol').catch(() => [])
      })
      .then((sigs: { protocol?: string; status: string }[]) => {
        const map: Record<string, SignatureBadgeStatus> = {}
        for (const s of sigs) {
          const pid = s.protocol
          if (!pid) continue
          const current = map[pid]
          if (s.status === 'rejected') map[pid] = 'rejected'
          else if (s.status === 'completed' && current !== 'rejected') map[pid] = 'completed'
          else if (s.status !== 'completed' && s.status !== 'rejected' && s.status !== 'failed' && s.status !== 'expired')
            map[pid] = current === 'rejected' ? current : 'pending'
        }
        setSignatureStatusMap(map)
      })
      .catch(() => setProtocols([]))
      .finally(() => setLoading(false))
  }, [directionFilter, searchQuery])

  const handleSearchChange = (value: string) => {
    setSearchInput(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setSearchQuery(value)
    }, 400)
  }

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleCreate = async (_payload: CreateProtocolPayload) => {
    load()
  }

  const handleArchive = async (p: ProtocolItem) => {
    if (!confirm('Archiviare questo protocollo?')) return
    await archiveProtocol(p.id)
    load()
  }

  const handleDownload = (p: ProtocolItem) => {
    downloadProtocolDocument(p.id).catch(() => alert('Download non disponibile.'))
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-lg bg-white shadow">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2">
        <h1 className="text-xl font-semibold text-slate-800">Protocollazione</h1>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => navigate('/protocols/registro-giornaliero')}
            className="rounded bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
          >
            Registro giornaliero
          </button>
          <button
            type="button"
            onClick={() => setFormOpen(true)}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Nuovo protocollo
          </button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-4">
        {loading ? (
          <p className="text-slate-500">Caricamento...</p>
        ) : (
          <ProtocolTable
            protocols={protocols}
            signatureStatusMap={signatureStatusMap}
            directionFilter={directionFilter}
            onDirectionFilterChange={setDirectionFilter}
            searchQuery={searchInput}
            onSearchChange={handleSearchChange}
            onView={(p) => navigate(`/protocols/${p.id}`)}
            onDownload={handleDownload}
            onArchive={handleArchive}
            onShare={(p) => setShareProtocolItem(p)}
          />
        )}
      </div>
      <ProtocolFormModal
        isOpen={formOpen}
        onClose={() => setFormOpen(false)}
        onSubmit={handleCreate}
      />
      {shareProtocolItem && (
        <ShareModal
          open={!!shareProtocolItem}
          onClose={() => setShareProtocolItem(null)}
          onSuccess={() => setShareProtocolItem(null)}
          shareProtocol={shareProtocol}
          targetId={shareProtocolItem.id}
          targetLabel={shareProtocolItem.subject || shareProtocolItem.protocol_id || 'Protocollo'}
        />
      )}
    </div>
  )
}
