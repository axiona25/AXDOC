import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getGroups, deleteGroup, type UserGroup } from '../services/groupService'

export function GroupsPage() {
  const [search, setSearch] = useState('')
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['groups', search],
    queryFn: () => getGroups(search ? { search } : undefined),
  })
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteGroup(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['groups'] }),
  })

  const groups = data?.results ?? []

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-800">Gruppi utenti</h1>
          <div className="flex gap-4">
            <Link to="/dashboard" className="text-slate-600 hover:underline">Dashboard</Link>
            <Link to="/users" className="text-slate-600 hover:underline">Utenti</Link>
          </div>
        </div>
      </header>
      <main className="p-6">
        <div className="mb-4 flex gap-2">
          <input
            type="text"
            placeholder="Cerca per nome..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="rounded-lg border border-slate-200 bg-white shadow">
          {isLoading ? (
            <p className="p-4 text-slate-600">Caricamento...</p>
          ) : (
            <table className="min-w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2 text-left text-sm font-medium text-slate-700">Nome</th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-slate-700">Membri</th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-slate-700">Data creazione</th>
                  <th className="px-4 py-2 text-right text-sm font-medium text-slate-700">Azioni</th>
                </tr>
              </thead>
              <tbody>
                {groups.map((g: UserGroup) => (
                  <tr key={g.id} className="border-t border-slate-100">
                    <td className="px-4 py-2">{g.name}</td>
                    <td className="px-4 py-2">{g.members_count}</td>
                    <td className="px-4 py-2 text-slate-600">{new Date(g.created_at).toLocaleDateString('it-IT')}</td>
                    <td className="px-4 py-2 text-right">
                      <Link to={`/groups/${g.id}`} className="text-indigo-600 hover:underline mr-2">Dettaglio</Link>
                      <button
                        type="button"
                        onClick={() => {
                          if (window.confirm(`Eliminare il gruppo "${g.name}"?`)) {
                            deleteMutation.mutate(g.id)
                          }
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
          )}
          {!isLoading && groups.length === 0 && (
            <p className="p-4 text-slate-500">Nessun gruppo. Crea un gruppo da Django Admin o aggiungi API di creazione.</p>
          )}
        </div>
      </main>
    </div>
  )
}
