import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { DossierList } from '../components/dossiers/DossierList'
import { DossierFormModal } from '../components/dossiers/DossierFormModal'
import { DossierCreateWizard } from '../components/dossiers/DossierCreateWizard'
import type { DossierItem, DossierDetailItem, CreateDossierPayload } from '../services/dossierService'
import { getDossiers, updateDossier, archiveDossier, deleteDossier } from '../services/dossierService'
import { getDossier } from '../services/dossierService'
import { getSignaturesByTarget } from '../services/signatureService'

export type SignatureBadgeStatus = 'pending' | 'completed' | 'rejected' | null

export function DossiersPage() {
  const navigate = useNavigate()
  const [dossiers, setDossiers] = useState<DossierItem[]>([])
  const [signatureStatusMap, setSignatureStatusMap] = useState<Record<string, SignatureBadgeStatus>>({})
  const [activeTab, setActiveTab] = useState<'mine' | 'all' | 'archived'>('mine')
  const [loading, setLoading] = useState(true)
  const [formOpen, setFormOpen] = useState(false)
  const [editingDossier, setEditingDossier] = useState<DossierDetailItem | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    const params: { filter?: 'mine' | 'all'; status?: string } = {}
    if (activeTab === 'all') params.filter = 'all'
    else if (activeTab === 'archived') params.status = 'archived'
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
  }, [activeTab])

  useEffect(() => {
    load()
  }, [load])

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

  return (
    <div className="flex flex-col rounded-lg bg-white shadow">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2">
        <h1 className="text-xl font-semibold text-slate-800">Fascicoli</h1>
        <button
          type="button"
          onClick={() => { setFormOpen(true); setEditingDossier(null); }}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Nuovo fascicolo
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-4">
        {loading ? (
          <p className="text-slate-500">Caricamento...</p>
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
          />
        )}
      </div>
      {editingDossier ? (
        <DossierFormModal
          isOpen={!!editingDossier}
          onClose={() => setEditingDossier(null)}
          onSubmit={handleUpdate}
          initial={editingDossier}
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
