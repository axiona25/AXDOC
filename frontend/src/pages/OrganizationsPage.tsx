import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  getOrganizationalUnitTree,
  getOrganizationalUnits,
  createOrganizationalUnit,
  updateOrganizationalUnit,
  exportMembers,
  type OrganizationalUnit,
} from '../services/organizationService'
import { OUTree } from '../components/organizations/OUTree'
import { OUMembersPanel } from '../components/organizations/OUMembersPanel'
import { OUFormModal } from '../components/organizations/OUFormModal'

export function OrganizationsPage() {
  const [mineOnly, setMineOnly] = useState(false)
  const [selectedOU, setSelectedOU] = useState<OrganizationalUnit | null>(null)
  const [ouModalOpen, setOuModalOpen] = useState(false)
  const [ouModalInitial, setOuModalInitial] = useState<OrganizationalUnit | null>(null)

  const { data: treeData, refetch: refetchTree } = useQuery({
    queryKey: ['org-tree'],
    queryFn: getOrganizationalUnitTree,
  })
  const { data: listData, refetch: refetchList } = useQuery({
    queryKey: ['org-list', mineOnly],
    queryFn: () => getOrganizationalUnits({ mine: mineOnly }),
  })
  const organizations = listData?.results ?? []
  const tree = treeData ?? []

  const handleExport = (ou: OrganizationalUnit) => {
    exportMembers(ou.id).then((blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `uo-${ou.code}-membri.csv`
      a.click()
      URL.revokeObjectURL(url)
    })
  }

  const handleOuSubmit = async (data: {
    name: string
    code: string
    description?: string
    parent?: string | null
  }) => {
    if (ouModalInitial) {
      await updateOrganizationalUnit(ouModalInitial.id, data)
    } else {
      await createOrganizationalUnit(data)
    }
    refetchTree()
    refetchList()
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-800">Unità Organizzative</h1>
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="text-slate-600 hover:underline">
              Dashboard
            </Link>
            <Link to="/users" className="text-slate-600 hover:underline">
              Utenti
            </Link>
            <button
              type="button"
              onClick={() => {
                setOuModalInitial(null)
                setOuModalOpen(true)
              }}
              className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
            >
              Nuova UO
            </button>
          </div>
        </div>
      </header>
      <main className="p-6">
        <div className="mb-4 flex items-center gap-4">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              checked={!mineOnly}
              onChange={() => setMineOnly(false)}
            />
            Tutte le UO
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              checked={mineOnly}
              onChange={() => setMineOnly(true)}
            />
            Le mie UO
          </label>
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="mb-3 font-semibold text-slate-800">Albero gerarchico</h2>
            <OUTree
              units={tree}
              selectedId={selectedOU?.id ?? null}
              onSelect={setSelectedOU}
              onEdit={(ou) => {
                setOuModalInitial(ou)
                setOuModalOpen(true)
              }}
              onExport={handleExport}
            />
          </div>
          <div>
            <OUMembersPanel
              ou={selectedOU}
              onExport={handleExport}
              onRefresh={() => {
                refetchTree()
                refetchList()
              }}
            />
          </div>
        </div>
      </main>
      <OUFormModal
        isOpen={ouModalOpen}
        onClose={() => { setOuModalOpen(false); setOuModalInitial(null) }}
        onSubmit={handleOuSubmit}
        initial={ouModalInitial}
        organizations={organizations}
      />
    </div>
  )
}
