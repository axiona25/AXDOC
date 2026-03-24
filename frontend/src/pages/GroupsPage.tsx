import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getGroups, createGroup, deleteGroup, type UserGroup } from '../services/groupService'
import { getOrganizationalUnits } from '../services/organizationService'

export function GroupsPage() {
  const [search, setSearch] = useState('')
  const [ouFilter, setOuFilter] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [newOuId, setNewOuId] = useState('')
  const [creating, setCreating] = useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['groups', search, ouFilter],
    queryFn: () =>
      getGroups({
        ...(search && { search }),
        ...(ouFilter && { ou: ouFilter }),
      }),
  })

  const { data: ouData } = useQuery({
    queryKey: ['organizations-list'],
    queryFn: () => getOrganizationalUnits({}),
  })
  const organizations = ouData?.results ?? []

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteGroup(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['groups'] }),
  })

  const handleCreate = async () => {
    if (!newName.trim()) return
    setCreating(true)
    try {
      await createGroup({
        name: newName.trim(),
        description: newDescription.trim() || undefined,
        organizational_unit: newOuId || undefined,
      })
      setNewName('')
      setNewDescription('')
      setNewOuId('')
      setCreateOpen(false)
      queryClient.invalidateQueries({ queryKey: ['groups'] })
    } catch {
      alert('Errore creazione gruppo.')
    } finally {
      setCreating(false)
    }
  }

  const groups = data?.results ?? []

  // Raggruppa per UO
  const groupsByOu = new Map<string, { ouName: string; groups: UserGroup[] }>()
  const ungrouped: UserGroup[] = []

  groups.forEach((g) => {
    if (g.organizational_unit && g.organizational_unit_name) {
      const key = g.organizational_unit
      if (!groupsByOu.has(key)) {
        groupsByOu.set(key, { ouName: g.organizational_unit_name, groups: [] })
      }
      groupsByOu.get(key)!.groups.push(g)
    } else {
      ungrouped.push(g)
    }
  })

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-800">Gruppi utenti</h1>
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="text-slate-600 hover:underline">
              Dashboard
            </Link>
            <Link to="/users" className="text-slate-600 hover:underline">
              Utenti
            </Link>
            <Link to="/organizations" className="text-slate-600 hover:underline">
              Organizzazioni
            </Link>
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Nuovo gruppo
            </button>
          </div>
        </div>
      </header>
      <main className="p-6">
        <div className="mb-4 flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Cerca per nome..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2 text-sm"
          />
          <select
            value={ouFilter}
            onChange={(e) => setOuFilter(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Tutte le U.O.</option>
            {organizations.map((ou) => (
              <option key={ou.id} value={ou.id}>
                {ou.name} ({ou.code})
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <p className="p-4 text-slate-600">Caricamento...</p>
        ) : (
          <div className="space-y-4">
            {/* Gruppi raggruppati per UO */}
            {Array.from(groupsByOu.entries()).map(([ouId, { ouName, groups: ouGroups }]) => (
              <div key={ouId} className="rounded-lg border border-slate-200 bg-white shadow">
                <div className="border-b border-slate-200 bg-slate-50 px-4 py-2">
                  <h2 className="text-sm font-semibold text-slate-700">🏢 {ouName}</h2>
                </div>
                <table className="min-w-full">
                  <thead className="bg-slate-50/50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Nome gruppo</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Descrizione</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Membri</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Data creazione</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-slate-600">Azioni</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ouGroups.map((g) => (
                      <tr key={g.id} className="border-t border-slate-100 hover:bg-slate-50">
                        <td className="px-4 py-2 text-sm font-medium text-slate-800">{g.name}</td>
                        <td className="max-w-[200px] truncate px-4 py-2 text-sm text-slate-500">
                          {g.description || '—'}
                        </td>
                        <td className="px-4 py-2 text-sm">{g.members_count}</td>
                        <td className="px-4 py-2 text-sm text-slate-600">
                          {new Date(g.created_at).toLocaleDateString('it-IT')}
                        </td>
                        <td className="px-4 py-2 text-right text-sm">
                          <Link to={`/groups/${g.id}`} className="mr-2 text-indigo-600 hover:underline">
                            Dettaglio
                          </Link>
                          <button
                            type="button"
                            onClick={() => {
                              if (window.confirm(`Eliminare "${g.name}"?`)) deleteMutation.mutate(g.id)
                            }}
                            className="text-red-600 hover:underline"
                          >
                            Elimina
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}

            {/* Gruppi senza UO */}
            {ungrouped.length > 0 && (
              <div className="rounded-lg border border-slate-200 bg-white shadow">
                <div className="border-b border-amber-200 bg-amber-50 px-4 py-2">
                  <h2 className="text-sm font-semibold text-amber-700">Gruppi senza U.O. assegnata</h2>
                </div>
                <table className="min-w-full">
                  <thead className="bg-slate-50/50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Nome gruppo</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Descrizione</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Membri</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Data creazione</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-slate-600">Azioni</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ungrouped.map((g) => (
                      <tr key={g.id} className="border-t border-slate-100 hover:bg-slate-50">
                        <td className="px-4 py-2 text-sm font-medium text-slate-800">{g.name}</td>
                        <td className="max-w-[200px] truncate px-4 py-2 text-sm text-slate-500">
                          {g.description || '—'}
                        </td>
                        <td className="px-4 py-2 text-sm">{g.members_count}</td>
                        <td className="px-4 py-2 text-sm text-slate-600">
                          {new Date(g.created_at).toLocaleDateString('it-IT')}
                        </td>
                        <td className="px-4 py-2 text-right text-sm">
                          <Link to={`/groups/${g.id}`} className="mr-2 text-indigo-600 hover:underline">
                            Dettaglio
                          </Link>
                          <button
                            type="button"
                            onClick={() => {
                              if (window.confirm(`Eliminare "${g.name}"?`)) deleteMutation.mutate(g.id)
                            }}
                            className="text-red-600 hover:underline"
                          >
                            Elimina
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {groups.length === 0 && <p className="p-4 text-slate-500">Nessun gruppo trovato.</p>}
          </div>
        )}
      </main>

      {/* Modal creazione gruppo */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-slate-800">Nuovo gruppo</h2>
            <div className="flex flex-col gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">Nome *</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  placeholder="Nome del gruppo"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Unità Organizzativa *</label>
                <select
                  value={newOuId}
                  onChange={(e) => setNewOuId(e.target.value)}
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">— Seleziona U.O. —</option>
                  {organizations.map((ou) => (
                    <option key={ou.id} value={ou.id}>
                      {ou.name} ({ou.code})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Descrizione</label>
                <textarea
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  rows={2}
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setCreateOpen(false)}
                className="rounded bg-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-300"
              >
                Annulla
              </button>
              <button
                type="button"
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
                className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {creating ? 'Creazione...' : 'Crea gruppo'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
