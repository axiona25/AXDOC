import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ProtocolTable } from '../components/protocols/ProtocolTable'
import { ProtocolFormModal } from '../components/protocols/ProtocolFormModal'
import { ShareModal } from '../components/sharing/ShareModal'
import { FilterPanel, type FilterField } from '../components/common/FilterPanel'
import type { ProtocolItem, CreateProtocolPayload } from '../services/protocolService'
import { getProtocols, archiveProtocol, downloadProtocolDocument } from '../services/protocolService'
import { exportProtocolsExcel, exportProtocolsPdf } from '../services/exportService'
import { shareProtocol } from '../services/sharingService'
import { getSignaturesByTarget } from '../services/signatureService'
import { getOrganizationalUnits } from '../services/organizationService'

export type SignatureBadgeStatus = 'pending' | 'completed' | 'rejected' | null

export function ProtocolsPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [protocols, setProtocols] = useState<ProtocolItem[]>([])
  const [signatureStatusMap, setSignatureStatusMap] = useState<Record<string, SignatureBadgeStatus>>({})
  const [directionFilter, setDirectionFilter] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [loading, setLoading] = useState(true)
  const [formOpen, setFormOpen] = useState(false)
  const [shareProtocolItem, setShareProtocolItem] = useState<ProtocolItem | null>(null)
  const [ouOptions, setOuOptions] = useState<{ value: string; label: string }[]>([])

  const ouIdQ = searchParams.get('ou_id') ?? ''
  const dateFromQ = searchParams.get('date_from') ?? ''
  const dateToQ = searchParams.get('date_to') ?? ''

  useEffect(() => {
    getOrganizationalUnits({ page: 1 })
      .then((r) =>
        setOuOptions((r.results ?? []).map((o) => ({ value: o.id, label: `${o.name} (${o.code})` }))),
      )
      .catch(() => setOuOptions([]))
  }, [])

  const filterFields = useMemo<FilterField[]>(
    () => [
      { name: 'ou_id', label: 'Unità organizzativa', type: 'select', options: ouOptions },
      { name: 'date_from', label: 'Data da', type: 'date' },
      { name: 'date_to', label: 'Data a', type: 'date' },
    ],
    [ouOptions],
  )

  const load = useCallback(() => {
    setLoading(true)
    const direction = directionFilter
    const params: {
      direction?: string
      search?: string
      page?: number
      ou_id?: string
      date_from?: string
      date_to?: string
    } = {}
    if (direction === 'in' || direction === 'out') params.direction = direction
    if (searchQuery.trim()) params.search = searchQuery.trim()
    if (ouIdQ) params.ou_id = ouIdQ
    if (dateFromQ) params.date_from = dateFromQ
    if (dateToQ) params.date_to = dateToQ
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
  }, [directionFilter, searchQuery, ouIdQ, dateFromQ, dateToQ])

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

  const buildExportParams = (): Record<string, string | undefined> => {
    const p: Record<string, string | undefined> = {}
    const d = directionFilter
    if (d === 'in' || d === 'out') p.direction = d
    if (searchQuery.trim()) p.search = searchQuery.trim()
    if (ouIdQ) p.ou_id = ouIdQ
    if (dateFromQ) p.date_from = dateFromQ
    if (dateToQ) p.date_to = dateToQ
    return p
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-lg border border-slate-200 bg-white shadow dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2 dark:border-slate-700">
        <h1 className="text-xl font-semibold text-slate-800 dark:text-slate-100">Protocollazione</h1>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => navigate('/protocols/registro-giornaliero')}
            className="rounded bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
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
      <div className="border-b border-slate-100 px-4 py-2 dark:border-slate-700">
        <FilterPanel fields={filterFields} onApply={() => load()} onReset={() => load()} />
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-4">
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Caricamento...</p>
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
            onExportExcel={() => exportProtocolsExcel(buildExportParams())}
            onExportPdf={() => exportProtocolsPdf(buildExportParams())}
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
