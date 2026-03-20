import type { OrganizationalUnit, OUMember } from '../../services/organizationService'
import { getOUMembers, addMember, removeMember } from '../../services/organizationService'
import { getUsers } from '../../services/userService'
import { useState, useEffect } from 'react'
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

  useEffect(() => {
    if (!ou) {
      setMembers([])
      return
    }
    setLoading(true)
    getOUMembers(ou.id)
      .then((data) => { setMembers(Array.isArray(data) ? data : []); setLoading(false) })
      .catch(() => setLoading(false))
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

  if (!ou) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-6 text-center text-slate-500">
        Seleziona un'unità organizzativa
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold text-slate-800">Membri — {ou.name}</h3>
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
                  <option key={v} value={v}>{l}</option>
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
  )
}
