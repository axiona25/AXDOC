import type { OrganizationalUnit, OUMember } from '../../services/organizationService'
import { getOUMembers, addMember, removeMember } from '../../services/organizationService'
import { getUsers } from '../../services/userService'
import { getGroups, createGroup, deleteGroup, type UserGroup } from '../../services/groupService'
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import type { User } from '../../types/auth'

interface OUMembersPanelProps {
  ou: OrganizationalUnit | null
  onExport: (ou: OrganizationalUnit) => void
  onRefresh: () => void
}

const OU_ROLE_LABELS: Record<string, string> = {
  OPERATOR: 'Operatore',
  REVIEWER: 'Revisore',
  APPROVER: 'Approvatore',
}

export function OUMembersPanel({ ou, onExport, onRefresh }: OUMembersPanelProps) {
  const [members, setMembers] = useState<OUMember[]>([])
  const [allUsers, setAllUsers] = useState<User[]>([])
  const [adding, setAdding] = useState(false)
  const [selectedUserId, setSelectedUserId] = useState('')
  const [selectedRole, setSelectedRole] = useState('OPERATOR')
  const [loading, setLoading] = useState(false)

  // Gruppi
  const [groups, setGroups] = useState<UserGroup[]>([])
  const [groupsLoading, setGroupsLoading] = useState(false)
  const [createGroupOpen, setCreateGroupOpen] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')
  const [newGroupDescription, setNewGroupDescription] = useState('')
  const [creatingGroup, setCreatingGroup] = useState(false)

  useEffect(() => {
    if (!ou) {
      setMembers([])
      setGroups([])
      return
    }
    setLoading(true)
    getOUMembers(ou.id)
      .then((data) => {
        setMembers(Array.isArray(data) ? data : [])
        setLoading(false)
      })
      .catch(() => setLoading(false))

    setGroupsLoading(true)
    getGroups({ ou: ou.id })
      .then((r) => {
        setGroups(r.results ?? [])
        setGroupsLoading(false)
      })
      .catch(() => {
        setGroups([])
        setGroupsLoading(false)
      })
  }, [ou?.id])

  useEffect(() => {
    getUsers({}).then((r) => setAllUsers(r.results ?? []))
  }, [])

  const handleAdd = async () => {
    if (!ou || !selectedUserId) return
    try {
      await addMember(ou.id, selectedUserId, selectedRole)
      onRefresh()
      const data = await getOUMembers(ou.id)
      setMembers(Array.isArray(data) ? data : [])
      setAdding(false)
      setSelectedUserId('')
    } catch {
      // ignore
    }
  }

  const handleRemove = async (userId: string) => {
    if (!ou) return
    try {
      await removeMember(ou.id, userId)
      setMembers((prev) => prev.filter((m) => m.user !== userId))
      onRefresh()
    } catch {
      // ignore
    }
  }

  const handleCreateGroup = async () => {
    if (!ou || !newGroupName.trim()) return
    setCreatingGroup(true)
    try {
      await createGroup({
        name: newGroupName.trim(),
        description: newGroupDescription.trim() || undefined,
        organizational_unit: ou.id,
      })
      setNewGroupName('')
      setNewGroupDescription('')
      setCreateGroupOpen(false)
      const r = await getGroups({ ou: ou.id })
      setGroups(r.results ?? [])
    } catch {
      alert('Errore creazione gruppo.')
    } finally {
      setCreatingGroup(false)
    }
  }

  const handleDeleteGroup = async (group: UserGroup) => {
    if (!window.confirm(`Eliminare il gruppo "${group.name}"?`)) return
    try {
      await deleteGroup(group.id)
      setGroups((prev) => prev.filter((g) => g.id !== group.id))
    } catch {
      alert('Errore eliminazione gruppo.')
    }
  }

  if (!ou) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-6 text-center text-slate-500">
        Seleziona un&apos;unità organizzativa per vedere membri e gruppi
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* MEMBRI */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">👥 Membri — {ou.name}</h3>
          <button
            type="button"
            onClick={() => onExport(ou)}
            className="rounded border border-slate-300 px-2 py-1 text-sm text-slate-700 hover:bg-slate-50"
          >
            Esporta CSV
          </button>
        </div>
        {loading ? (
          <p className="text-sm text-slate-500">Caricamento...</p>
        ) : (
          <>
            <ul className="mb-4 space-y-2">
              {members.map((m) => (
                <li
                  key={m.id}
                  className="flex items-center justify-between rounded border border-slate-100 px-3 py-2 text-sm"
                >
                  <span>
                    {m.user_name} ({m.user_email}) — {OU_ROLE_LABELS[m.role] ?? m.role}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleRemove(m.user)}
                    className="text-red-600 hover:underline"
                  >
                    Rimuovi
                  </button>
                </li>
              ))}
              {members.length === 0 && (
                <p className="text-sm text-slate-500">Nessun membro in questa U.O.</p>
              )}
            </ul>
            {adding ? (
              <div className="flex flex-wrap items-center gap-2 rounded border border-slate-200 p-2">
                <select
                  value={selectedUserId}
                  onChange={(e) => setSelectedUserId(e.target.value)}
                  className="rounded border border-slate-300 px-2 py-1 text-sm"
                >
                  <option value="">Seleziona utente</option>
                  {allUsers
                    .filter((u) => !members.some((m) => m.user === u.id))
                    .map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.first_name} {u.last_name} ({u.email})
                      </option>
                    ))}
                </select>
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  className="rounded border border-slate-300 px-2 py-1 text-sm"
                >
                  {Object.entries(OU_ROLE_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleAdd}
                  className="rounded bg-indigo-600 px-2 py-1 text-sm text-white hover:bg-indigo-700"
                >
                  Aggiungi
                </button>
                <button
                  type="button"
                  onClick={() => setAdding(false)}
                  className="rounded border border-slate-300 px-2 py-1 text-sm"
                >
                  Annulla
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setAdding(true)}
                className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
              >
                + Aggiungi utente
              </button>
            )}
          </>
        )}
      </div>

      {/* GRUPPI */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">📂 Gruppi — {ou.name}</h3>
          <button
            type="button"
            onClick={() => setCreateGroupOpen(!createGroupOpen)}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700"
          >
            + Nuovo gruppo
          </button>
        </div>

        {createGroupOpen && (
          <div className="mb-4 space-y-2 rounded border border-indigo-200 bg-indigo-50/50 p-3">
            <input
              type="text"
              placeholder="Nome del gruppo *"
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
            />
            <input
              type="text"
              placeholder="Descrizione (facoltativa)"
              value={newGroupDescription}
              onChange={(e) => setNewGroupDescription(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleCreateGroup}
                disabled={creatingGroup || !newGroupName.trim()}
                className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {creatingGroup ? 'Creazione...' : 'Crea'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setCreateGroupOpen(false)
                  setNewGroupName('')
                  setNewGroupDescription('')
                }}
                className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50"
              >
                Annulla
              </button>
            </div>
          </div>
        )}

        {groupsLoading ? (
          <p className="text-sm text-slate-500">Caricamento gruppi...</p>
        ) : groups.length > 0 ? (
          <ul className="space-y-2">
            {groups.map((g) => (
              <li
                key={g.id}
                className="flex items-center justify-between rounded border border-slate-100 px-3 py-2 text-sm hover:bg-slate-50"
              >
                <div>
                  <span className="font-medium text-slate-800">{g.name}</span>
                  {g.description && (
                    <span className="ml-2 text-xs text-slate-500">{g.description}</span>
                  )}
                  <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                    {g.members_count} membr{g.members_count === 1 ? 'o' : 'i'}
                  </span>
                </div>
                <div className="flex gap-2">
                  <Link to={`/groups/${g.id}`} className="text-xs text-indigo-600 hover:underline">
                    Dettaglio
                  </Link>
                  <button
                    type="button"
                    onClick={() => handleDeleteGroup(g)}
                    className="text-xs text-red-600 hover:underline"
                  >
                    Elimina
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">Nessun gruppo in questa U.O. Crea il primo gruppo.</p>
        )}
      </div>
    </div>
  )
}
