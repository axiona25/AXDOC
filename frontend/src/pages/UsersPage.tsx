import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import type { User } from '../types/auth'
import { getUsers, deleteUser, getUser } from '../services/userService'
import { UserTable } from '../components/users/UserTable'
import { InviteUserModal } from '../components/users/InviteUserModal'
import { ImportUsersModal } from '../components/users/ImportUsersModal'
import { CreateUserModal } from '../components/users/CreateUserModal'
import { EditUserModal } from '../components/users/EditUserModal'
import { getOrganizationalUnits } from '../services/organizationService'

export function UsersPage() {
  const [roleFilter, setRoleFilter] = useState('')
  const [userTypeFilter, setUserTypeFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['users', roleFilter, userTypeFilter, activeFilter, search, page],
    queryFn: () =>
      getUsers({
        ...(roleFilter && { role: roleFilter }),
        ...(userTypeFilter && { user_type: userTypeFilter as 'internal' | 'guest' }),
        ...(activeFilter && { is_active: activeFilter === 'true' }),
        ...(search && { search }),
        page,
      }),
  })

  const { data: ouData } = useQuery({
    queryKey: ['organizations-list'],
    queryFn: () => getOrganizationalUnits({}),
  })
  const organizations = ouData?.results ?? []

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-900">
      <header className="border-b border-slate-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-800">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Gestione Utenti</h1>
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="text-slate-600 hover:underline dark:text-slate-300">
              Dashboard
            </Link>
            <Link to="/organizations" className="text-slate-600 hover:underline dark:text-slate-300">
              Organizzazioni
            </Link>
            <button
              type="button"
              onClick={() => setImportOpen(true)}
              className="rounded border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              Importa utenti
            </button>
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              className="rounded border border-indigo-600 px-4 py-2 text-sm text-indigo-600 hover:bg-indigo-50 dark:border-indigo-400 dark:text-indigo-400 dark:hover:bg-indigo-950/50"
            >
              Nuovo utente
            </button>
            <button
              type="button"
              onClick={() => setInviteOpen(true)}
              className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
            >
              Invita utente
            </button>
          </div>
        </div>
      </header>
      <div className="p-6">
        <UserTable
          data={data}
          isLoading={isLoading}
          onEdit={(user) => {
            setEditingUser(user)
            setEditOpen(true)
          }}
          onDelete={async (user) => {
            if (window.confirm(`Eliminare ${user.email}?`)) {
              await deleteUser(user.id)
              refetch()
            }
          }}
          roleFilter={roleFilter}
          onRoleFilterChange={setRoleFilter}
          userTypeFilter={userTypeFilter}
          onUserTypeFilterChange={setUserTypeFilter}
          activeFilter={activeFilter}
          onActiveFilterChange={setActiveFilter}
          search={search}
          onSearchChange={setSearch}
          onPageChange={setPage}
        />
      </div>
      <CreateUserModal
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        onSuccess={() => refetch()}
        organizations={organizations}
      />
      <EditUserModal
        isOpen={editOpen}
        user={editingUser}
        onClose={() => {
          setEditOpen(false)
          setEditingUser(null)
        }}
        onSuccess={async () => {
          refetch()
          if (editingUser) {
            try {
              const fresh = await getUser(editingUser.id)
              setEditingUser(fresh)
            } catch {
              setEditingUser(null)
            }
          }
        }}
        organizations={organizations}
      />
      <InviteUserModal
        isOpen={inviteOpen}
        onClose={() => setInviteOpen(false)}
        onSuccess={() => refetch()}
        organizations={organizations}
      />
      <ImportUsersModal
        isOpen={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={() => refetch()}
      />
    </div>
  )
}
