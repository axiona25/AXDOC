import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { DossierList } from '../components/dossiers/DossierList'
import { DossierFormModal } from '../components/dossiers/DossierFormModal'
import { DossierCreateWizard } from '../components/dossiers/DossierCreateWizard'
import { FilterPanel, type FilterField } from '../components/common/FilterPanel'
import type { DossierItem, DossierDetailItem, CreateDossierPayload } from '../services/dossierService'
import { getDossiers, updateDossier, archiveDossier, deleteDossier } from '../services/dossierService'
import { exportDossiersExcel, exportDossiersPdf } from '../services/exportService'
import { getDossier } from '../services/dossierService'
import { getSignaturesByTarget } from '../services/signatureService'
import { getUsers } from '../services/userService'
import { getOrganizationalUnits } from '../services/organizationService'

export type SignatureBadgeStatus = 'pending' | 'completed' | 'rejected' | null

export function DossiersPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [dossiers, setDossiers] = useState<DossierItem[]>([])
  const [signatureStatusMap, setSignatureStatusMap] = useState<Record<string, SignatureBadgeStatus>>({})
  const [activeTab, setActiveTab] = useState<'mine' | 'all' | 'archived'>('mine')
  const [loading, setLoading] = useState(true)
  const [formOpen, setFormOpen] = useState(false)
  const [editingDossier, setEditingDossier] = useState<DossierDetailItem | null>(null)
  const [users, setUsers] = useState<{ id: string; email: string; first_name?: string; last_name?: string }[]>([])
  const [ouOptions, setOuOptions] = useState<{ value: string; label: string }[]>([])

  const responsibleIdQ = searchParams.get('responsible_id') ?? ''
  const ouIdQ = searchParams.get('ou_id') ?? ''
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  const userOptions = useMemo(
    () =>
      users.map((u) => ({
        value: u.id,
        label: [u.first_name, u.last_name].filter(Boolean).join(' ').trim() || u.email,
      })),
    [users],
  )

  const filterFields = useMemo<FilterField[]>(
    () => [
      { name: 'responsible_id', label: 'Responsabile', type: 'select', options: userOptions },
      { name: 'ou_id', label: 'Unità organizzativa', type: 'select', options: ouOptions },
    ],
    [userOptions, ouOptions],
  )

  useEffect(() => {
    getOrganizationalUnits({ page: 1 })
      .then((r) =>
        setOuOptions((r.results ?? []).map((o) => ({ value: o.id, label: `${o.name} (${o.code})` }))),
      )
      .catch(() => setOuOptions([]))
  }, [])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchInput.trim()), 300)
    return () => clearTimeout(t)
  }, [searchInput])

  const load = useCallback(() => {
    setLoading(true)
    const params: {
      filter?: 'mine' | 'all'
      status?: string
      responsible_id?: string
      ou_id?: string
      search?: string
    } = {}
    if (activeTab === 'all') params.filter = 'all'
    else if (activeTab === 'archived') params.status = 'archived'
    if (responsibleIdQ) params.responsible_id = responsibleIdQ
    if (ouIdQ) params.ou_id = ouIdQ
    if (debouncedSearch) params.search = debouncedSearch
    getDossiers(params)
      .then((res) => {
        setDossiers(res.results || [])
        return getSignaturesByTarget('dossier').catch(() => [])
      })
      .then((sigs: { dossier?: string; status: string }[]) => {
        const map: Record<string, SignatureBadgeStatus> = {}
        for (const s of sigs) {
          const did = s.dossier
          if (!did) continue
          const current = map[did]
          if (s.status === 'rejected') map[did] = 'rejected'
          else if (s.status === 'completed' && current !== 'rejected') map[did] = 'completed'
          else if (s.status !== 'completed' && s.status !== 'rejected' && s.status !== 'failed' && s.status !== 'expired')
            map[did] = current === 'rejected' ? current : 'pending'
        }
        setSignatureStatusMap(map)
      })
      .catch(() => setDossiers([]))
      .finally(() => setLoading(false))
  }, [activeTab, responsibleIdQ, ouIdQ, debouncedSearch])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    getUsers({}).then((r) => setUsers(r.results ?? [])).catch(() => setUsers([]))
  }, [])

  const handleCreateSuccess = () => {
    load()
  }

  const handleUpdate = async (payload: CreateDossierPayload) => {
    if (!editingDossier) return
    await updateDossier(editingDossier.id, payload)
    setEditingDossier(null)
    load()
  }

  const handleArchive = async (d: DossierItem) => {
    if (!confirm('Archiviare questo fascicolo? Tutti i documenti devono essere approvati.')) return
    await archiveDossier(d.id)
    load()
  }

  const handleDelete = async (d: DossierItem) => {
    if (!confirm('Eliminare definitivamente questo fascicolo?')) return
    await deleteDossier(d.id)
    load()
  }

  const openEdit = (d: DossierItem) => {
    getDossier(d.id).then(setEditingDossier).catch(() => setEditingDossier(null))
  }

  const dossierExportParams = (): Record<string, string | undefined> => {
    const p: Record<string, string | undefined> = {}
    if (activeTab === 'all') p.filter = 'all'
    if (activeTab === 'archived') p.status = 'archived'
    if (responsibleIdQ) p.responsible_id = responsibleIdQ
    if (ouIdQ) p.ou_id = ouIdQ
    if (debouncedSearch) p.search = debouncedSearch
    return p
  }

  return (
    <div className="flex flex-col rounded-lg border border-slate-200 bg-white shadow dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2 dark:border-slate-700">
        <h1 className="text-xl font-semibold text-slate-800 dark:text-slate-100">Fascicoli</h1>
        <button
          type="button"
          onClick={() => {
            setFormOpen(true)
            setEditingDossier(null)
          }}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Nuovo fascicolo
        </button>
      </div>
      <div className="border-b border-slate-100 px-4 py-2 dark:border-slate-700">
        <div className="mb-3">
          <label htmlFor="dossier-search" className="sr-only">
            Cerca fascicoli
          </label>
          <input
            id="dossier-search"
            type="search"
            placeholder="Cerca fascicoli..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full max-w-md rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder-slate-400"
          />
        </div>
        <FilterPanel fields={filterFields} onApply={() => load()} onReset={() => load()} />
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-4">
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Caricamento...</p>
        ) : (
          <DossierList
            dossiers={dossiers}
            signatureStatusMap={signatureStatusMap}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onOpen={(d) => navigate(`/dossiers/${d.id}`)}
            onEdit={openEdit}
            onArchive={handleArchive}
            onDelete={handleDelete}
            onExportExcel={() => exportDossiersExcel(dossierExportParams())}
            onExportPdf={() => exportDossiersPdf(dossierExportParams())}
          />
        )}
      </div>
      {editingDossier ? (
        <DossierFormModal
          isOpen={!!editingDossier}
          onClose={() => setEditingDossier(null)}
          onSubmit={handleUpdate}
          initial={editingDossier}
          users={users}
        />
      ) : (
        <DossierCreateWizard
          isOpen={formOpen}
          onClose={() => setFormOpen(false)}
          onSuccess={handleCreateSuccess}
        />
      )}
    </div>
  )
}
