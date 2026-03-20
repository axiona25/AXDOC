import type { User } from '../../types/auth'
import type { UsersResponse } from '../../services/userService'

interface UserTableProps {
  data: UsersResponse | undefined
  isLoading: boolean
  onEdit: (user: User) => void
  onDisable?: (user: User) => void
  onDelete?: (user: User) => void
  roleFilter: string
  onRoleFilterChange: (v: string) => void
  userTypeFilter: string
  onUserTypeFilterChange: (v: string) => void
  activeFilter: string
  onActiveFilterChange: (v: string) => void
  search: string
  onSearchChange: (v: string) => void
  onPageChange?: (page: number) => void
}

const ROLE_LABELS: Record<string, string> = {
  OPERATOR: 'Operatore',
  REVIEWER: 'Revisore',
  APPROVER: 'Approvatore',
  ADMIN: 'Amministratore',
}

export function UserTable({
  data,
  isLoading,
  onEdit,
  onDisable,
  onDelete,
  roleFilter,
  onRoleFilterChange,
  userTypeFilter,
  onUserTypeFilterChange,
  activeFilter,
  onActiveFilterChange,
  search,
  onSearchChange,
  onPageChange,
}: UserTableProps) {
  const users = data?.results ?? []
  const count = data?.count ?? 0
  const next = data?.next
  const previous = data?.previous

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <input
          type="text"
          placeholder="Cerca nome o email..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <select
          value={roleFilter}
          onChange={(e) => onRoleFilterChange(e.target.value)}
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Tutti i ruoli</option>
          {Object.entries(ROLE_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
        <select
          value={userTypeFilter}
          onChange={(e) => onUserTypeFilterChange(e.target.value)}
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Tutti i tipi</option>
          <option value="internal">Interni</option>
          <option value="guest">Ospiti</option>
        </select>
        <select
          value={activeFilter}
          onChange={(e) => onActiveFilterChange(e.target.value)}
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Tutti</option>
          <option value="true">Attivi</option>
          <option value="false">Disattivati</option>
        </select>
      </div>
      {isLoading ? (
        <p className="text-slate-500">Caricamento...</p>
      ) : (
        <>
          <div className="overflow-x-auto rounded border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Nome</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Email</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Tipo</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Ruolo</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">U.O.</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Stato</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-600">Data creazione</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-slate-600">Azioni</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="px-4 py-2 text-sm text-slate-800">
                      {user.first_name} {user.last_name}
                    </td>
                    <td className="px-4 py-2 text-sm text-slate-600">{user.email}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`inline rounded px-2 py-0.5 text-xs font-medium ${
                          user.is_guest || user.user_type === 'guest'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {user.is_guest || user.user_type === 'guest' ? 'Ospite' : 'Interno'}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-sm">{ROLE_LABELS[user.role] ?? user.role}</td>
                    <td className="px-4 py-2 text-sm">
                      {user.organizational_units && user.organizational_units.length > 0 ? (
                        <span className="text-slate-800">
                          {user.organizational_units.map((ou) => ou.name).join(', ')}
                        </span>
                      ) : (
                        <span className="italic text-slate-400">In attesa di assegnazione</span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`inline rounded px-2 py-0.5 text-xs ${
                          user.is_active ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {user.is_active ? 'Attivo' : 'Disattivo'}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-sm text-slate-500">
                      {user.date_joined ? new Date(user.date_joined).toLocaleDateString('it-IT') : '-'}
                    </td>
                    <td className="px-4 py-2 text-right text-sm">
                      <button
                        type="button"
                        onClick={() => onEdit(user)}
                        className="text-indigo-600 hover:underline"
                      >
                        Modifica
                      </button>
                      {onDisable && user.is_active && (
                        <>
                          {' · '}
                          <button
                            type="button"
                            onClick={() => onDisable(user)}
                            className="text-amber-600 hover:underline"
                          >
                            Disattiva
                          </button>
                        </>
                      )}
                      {onDelete && (
                        <>
                          {' · '}
                          <button
                            type="button"
                            onClick={() => onDelete(user)}
                            className="text-red-600 hover:underline"
                          >
                            Elimina
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {count > 0 && (
            <div className="flex items-center justify-between text-sm text-slate-600">
              <span>Totale: {count} utenti</span>
              {onPageChange && (next || previous) && (
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={!previous}
                    onClick={() => previous && onPageChange(parsePage(previous))}
                    className="rounded border px-2 py-1 disabled:opacity-50"
                  >
                    Precedente
                  </button>
                  <button
                    type="button"
                    disabled={!next}
                    onClick={() => next && onPageChange(parsePage(next))}
                    className="rounded border px-2 py-1 disabled:opacity-50"
                  >
                    Successiva
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function parsePage(url: string): number {
  const m = url.match(/page=(\d+)/)
  return m ? parseInt(m[1], 10) : 1
}
