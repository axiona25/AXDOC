import { useState, useEffect, type ReactNode } from 'react'
import type { User } from '../../types/auth'
import {
  updateUser,
  resetUserPassword,
  getUserPermissions,
  setUserPermission,
  type UpdateUserData,
  type UserPermissions,
} from '../../services/userService'
import { getDocuments } from '../../services/documentService'
import type { DocumentItem } from '../../services/documentService'
import { getDossiers } from '../../services/dossierService'
import type { DossierItem } from '../../services/dossierService'
import { getOrganizationalUnits, addMember, removeMember, type OrganizationalUnit } from '../../services/organizationService'
import { getGroups, addGroupMembers, removeGroupMember, getGroupMembers, type UserGroup } from '../../services/groupService'

const ROLE_LABELS: Record<string, string> = {
  OPERATOR: 'Operatore',
  REVIEWER: 'Revisore',
  APPROVER: 'Approvatore',
  ADMIN: 'Amministratore',
}

type TabId = 'info' | 'uo' | 'groups' | 'permissions'

function PermissionFolder({
  name,
  count,
  defaultOpen = false,
  children,
}: {
  name: string
  count: number
  defaultOpen?: boolean
  children: ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  useEffect(() => {
    setOpen(defaultOpen)
  }, [defaultOpen])

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 border-b border-slate-200 bg-slate-50 px-3 py-2 text-left transition-colors hover:bg-slate-100"
      >
        <span
          className="text-xs text-slate-500 transition-transform"
          style={{ transform: open ? 'rotate(90deg)' : 'rotate(0deg)' }}
        >
          ▶
        </span>
        <span className="text-sm">📁</span>
        <span className="text-sm font-medium text-slate-700">{name}</span>
        <span className="text-xs text-slate-400">({count})</span>
      </button>
      {open ? <div>{children}</div> : null}
    </div>
  )
}

interface EditUserModalProps {
  isOpen: boolean
  user: User | null
  onClose: () => void
  onSuccess: () => void
  organizations?: OrganizationalUnit[]
}

export function EditUserModal({
  isOpen,
  user,
  onClose,
  onSuccess,
  organizations: _organizations = [],
}: EditUserModalProps) {
  const [tab, setTab] = useState<TabId>('info')

  // Tab Info
  const [first_name, setFirst_name] = useState('')
  const [last_name, setLast_name] = useState('')
  const [role, setRole] = useState<string>('OPERATOR')
  const [user_type, setUser_type] = useState<'internal' | 'guest'>('internal')
  const [is_active, setIs_active] = useState(true)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [resetLoading, setResetLoading] = useState(false)
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null)
  const [infoSaved, setInfoSaved] = useState(false)

  // Tab UO
  const [allOUs, setAllOUs] = useState<OrganizationalUnit[]>([])
  const [userOUIds, setUserOUIds] = useState<Set<string>>(new Set())
  const [ouLoading, setOuLoading] = useState(false)
  const [ouSearching, setOuSearching] = useState('')

  // Tab Gruppi
  const [allGroups, setAllGroups] = useState<UserGroup[]>([])
  const [userGroupIds, setUserGroupIds] = useState<Set<string>>(new Set())
  const [groupsLoading, setGroupsLoading] = useState(false)
  const [groupSearching, setGroupSearching] = useState('')

  // Tab Permessi
  const [userPerms, setUserPerms] = useState<UserPermissions | null>(null)
  const [allDocs, setAllDocs] = useState<DocumentItem[]>([])
  const [allDossiers, setAllDossiers] = useState<DossierItem[]>([])
  const [addingPerm, setAddingPerm] = useState(false)
  const [permDocSearch, setPermDocSearch] = useState('')

  useEffect(() => {
    if (!user || !isOpen) return
    setFirst_name(user.first_name ?? '')
    setLast_name(user.last_name ?? '')
    setRole(user.role ?? 'OPERATOR')
    setUser_type((user.user_type as 'internal' | 'guest') ?? 'internal')
    setIs_active(user.is_active ?? true)
    setErrors({})
    setGeneratedPassword(null)
    setInfoSaved(false)
    setTab('info')
    setPermDocSearch('')

    const ous = user.organizational_units ?? (user.organizational_unit ? [user.organizational_unit] : [])
    setUserOUIds(new Set(ous.map((o) => o.id)))

    getOrganizationalUnits({})
      .then((r) => setAllOUs(r.results ?? []))
      .catch(() => setAllOUs([]))

    getGroups({})
      .then(async (r) => {
        const groups = r.results ?? []
        setAllGroups(groups)
        const memberSet = new Set<string>()
        for (const g of groups) {
          try {
            const members = await getGroupMembers(g.id)
            if (members.some((m) => m.user === user.id)) {
              memberSet.add(g.id)
            }
          } catch {
            /* ignore */
          }
        }
        setUserGroupIds(memberSet)
      })
      .catch(() => setAllGroups([]))

    getUserPermissions(user.id).then(setUserPerms).catch(() => setUserPerms(null))
    getDocuments({ page: 1 })
      .then((r) => setAllDocs(r.results || []))
      .catch(() => setAllDocs([]))
    getDossiers({})
      .then((r) => setAllDossiers(r.results || []))
      .catch(() => setAllDossiers([]))
  }, [user, isOpen])

  const handleSaveInfo = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!user) return
    setErrors({})
    if (!first_name.trim()) {
      setErrors({ first_name: 'Obbligatorio' })
      return
    }
    if (!last_name.trim()) {
      setErrors({ last_name: 'Obbligatorio' })
      return
    }
    setLoading(true)
    try {
      const payload: UpdateUserData = {
        first_name: first_name.trim(),
        last_name: last_name.trim(),
        role,
        user_type,
        is_active,
      }
      await updateUser(user.id, payload)
      setInfoSaved(true)
      onSuccess()
      setTimeout(() => setInfoSaved(false), 2000)
    } catch {
      setErrors({ _form: 'Errore salvataggio.' })
    } finally {
      setLoading(false)
    }
  }

  const handleResetPassword = async () => {
    if (!user || !window.confirm('Reimpostare la password?')) return
    setResetLoading(true)
    try {
      const res = await resetUserPassword(user.id)
      setGeneratedPassword(res.generated_password)
    } catch {
      alert('Errore reset password.')
    } finally {
      setResetLoading(false)
    }
  }

  const handleToggleOU = async (ouId: string) => {
    if (!user) return
    setOuLoading(true)
    try {
      if (userOUIds.has(ouId)) {
        await removeMember(ouId, user.id)
        setUserOUIds((prev) => {
          const next = new Set(prev)
          next.delete(ouId)
          return next
        })
      } else {
        await addMember(ouId, user.id, 'OPERATOR')
        setUserOUIds((prev) => new Set(prev).add(ouId))
      }
      onSuccess()
    } catch {
      alert('Errore aggiornamento UO.')
    } finally {
      setOuLoading(false)
    }
  }

  const handleToggleGroup = async (groupId: string) => {
    if (!user) return
    setGroupsLoading(true)
    try {
      if (userGroupIds.has(groupId)) {
        await removeGroupMember(groupId, user.id)
        setUserGroupIds((prev) => {
          const next = new Set(prev)
          next.delete(groupId)
          return next
        })
      } else {
        await addGroupMembers(groupId, [user.id])
        setUserGroupIds((prev) => new Set(prev).add(groupId))
      }
      onSuccess()
    } catch {
      alert('Errore aggiornamento gruppo.')
    } finally {
      setGroupsLoading(false)
    }
  }

  const handleAddDocPermission = async (docId: string) => {
    if (!user) return
    setAddingPerm(true)
    try {
      await setUserPermission(user.id, {
        type: 'document',
        target_id: docId,
        can_read: true,
        can_write: false,
      })
      const perms = await getUserPermissions(user.id)
      setUserPerms(perms)
    } catch {
      alert('Errore.')
    } finally {
      setAddingPerm(false)
    }
  }

  const handleRemoveDocPermission = async (docId: string) => {
    if (!user) return
    try {
      await setUserPermission(user.id, { type: 'document', target_id: docId, remove: true })
      const perms = await getUserPermissions(user.id)
      setUserPerms(perms)
    } catch {
      alert('Errore.')
    }
  }

  const handleToggleDocWrite = async (docId: string, currentWrite: boolean) => {
    if (!user) return
    try {
      await setUserPermission(user.id, {
        type: 'document',
        target_id: docId,
        can_read: true,
        can_write: !currentWrite,
      })
      const perms = await getUserPermissions(user.id)
      setUserPerms(perms)
    } catch {
      alert('Errore.')
    }
  }

  const handleAddDossierPermission = async (dossierId: string) => {
    if (!user) return
    setAddingPerm(true)
    try {
      await setUserPermission(user.id, {
        type: 'dossier',
        target_id: dossierId,
        can_read: true,
        can_write: false,
      })
      const perms = await getUserPermissions(user.id)
      setUserPerms(perms)
    } catch {
      alert('Errore.')
    } finally {
      setAddingPerm(false)
    }
  }

  const handleRemoveDossierPermission = async (dossierId: string) => {
    if (!user) return
    try {
      await setUserPermission(user.id, { type: 'dossier', target_id: dossierId, remove: true })
      const perms = await getUserPermissions(user.id)
      setUserPerms(perms)
    } catch {
      alert('Errore.')
    }
  }

  const handleToggleDossierWrite = async (dossierId: string, currentWrite: boolean) => {
    if (!user) return
    try {
      await setUserPermission(user.id, {
        type: 'dossier',
        target_id: dossierId,
        can_read: true,
        can_write: !currentWrite,
      })
      const perms = await getUserPermissions(user.id)
      setUserPerms(perms)
    } catch {
      alert('Errore.')
    }
  }

  if (!isOpen || !user) return null

  const tabs: { id: TabId; label: string; badge?: number }[] = [
    { id: 'info', label: 'Informazioni' },
    { id: 'uo', label: 'Unità Organizzative', badge: userOUIds.size },
    { id: 'groups', label: 'Gruppi', badge: userGroupIds.size },
    {
      id: 'permissions',
      label: 'Permessi',
      badge: (userPerms?.documents.length ?? 0) + (userPerms?.dossiers.length ?? 0),
    },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex w-full max-w-2xl flex-col rounded-lg bg-white shadow-xl" style={{ maxHeight: '85vh' }}>
        <div className="border-b border-slate-200 px-6 pb-0 pt-5">
          <div className="mb-2 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">Modifica utente</h2>
              <p className="text-sm text-slate-500">{user.email}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="text-xl text-slate-400 hover:text-slate-600"
              aria-label="Chiudi"
            >
              ✕
            </button>
          </div>
          <div className="flex gap-0">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={`border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                  tab === t.id
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                {t.label}
                {t.badge !== undefined && t.badge > 0 && (
                  <span className="ml-1.5 rounded-full bg-indigo-100 px-1.5 py-0.5 text-xs text-indigo-700">
                    {t.badge}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {tab === 'info' && (
            <form onSubmit={handleSaveInfo} className="space-y-4">
              {errors._form && (
                <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{errors._form}</div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Nome *</label>
                  <input
                    type="text"
                    value={first_name}
                    onChange={(e) => setFirst_name(e.target.value)}
                    className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  />
                  {errors.first_name && <p className="mt-1 text-xs text-red-600">{errors.first_name}</p>}
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Cognome *</label>
                  <input
                    type="text"
                    value={last_name}
                    onChange={(e) => setLast_name(e.target.value)}
                    className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  />
                  {errors.last_name && <p className="mt-1 text-xs text-red-600">{errors.last_name}</p>}
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Ruolo *</label>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(ROLE_LABELS).map(([v, l]) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => setRole(v)}
                      disabled={user_type === 'guest'}
                      className={`rounded border px-3 py-2 text-sm font-medium transition-colors ${
                        role === v
                          ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                          : 'border-slate-300 text-slate-600 hover:bg-slate-50'
                      } disabled:opacity-50`}
                    >
                      {l}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <span className="mb-2 block text-sm font-medium text-slate-700">Tipo utente</span>
                <div className="flex gap-3">
                  {(
                    [
                      { value: 'internal' as const, label: 'Interno', desc: 'Accesso pieno' },
                      { value: 'guest' as const, label: 'Ospite', desc: 'Solo condivisi' },
                    ] as const
                  ).map((topt) => (
                    <button
                      key={topt.value}
                      type="button"
                      onClick={() => {
                        setUser_type(topt.value)
                        if (topt.value === 'guest') setRole('OPERATOR')
                      }}
                      className={`flex-1 rounded border px-3 py-2 text-left text-sm transition-colors ${
                        user_type === topt.value
                          ? 'border-indigo-500 bg-indigo-50'
                          : 'border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <span className="font-medium">{topt.label}</span>
                      <span className="block text-xs text-slate-500">{topt.desc}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <label className="flex cursor-pointer items-center gap-2">
                  <input
                    type="checkbox"
                    checked={is_active}
                    onChange={(e) => setIs_active(e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-sm font-medium text-slate-700">Account attivo</span>
                </label>
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium ${
                    is_active ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  {is_active ? 'Attivo' : 'Disattivato'}
                </span>
              </div>

              <div className="border-t border-slate-200 pt-3">
                {generatedPassword ? (
                  <div className="rounded border border-yellow-300 bg-yellow-50 p-3">
                    <p className="mb-1 text-sm font-semibold text-yellow-800">✅ Password temporanea:</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 select-all rounded bg-white px-3 py-1.5 font-mono text-sm">
                        {generatedPassword}
                      </code>
                      <button
                        type="button"
                        onClick={() => navigator.clipboard.writeText(generatedPassword)}
                        className="rounded border px-2 py-1 text-xs hover:bg-yellow-100"
                      >
                        Copia
                      </button>
                    </div>
                    <p className="mt-1 text-xs text-yellow-700">
                      L&apos;utente dovrà cambiarla al primo accesso.
                    </p>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={handleResetPassword}
                    disabled={resetLoading}
                    className="text-sm text-orange-600 underline hover:text-orange-800 disabled:opacity-50"
                  >
                    {resetLoading ? 'Reimpostazione...' : '🔑 Reimposta password'}
                  </button>
                )}
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className={`rounded px-4 py-2 text-sm font-medium text-white transition-colors disabled:opacity-50 ${
                    infoSaved ? 'bg-green-600' : 'bg-indigo-600 hover:bg-indigo-700'
                  }`}
                >
                  {loading ? 'Salvataggio...' : infoSaved ? '✓ Salvato' : 'Salva informazioni'}
                </button>
              </div>
            </form>
          )}

          {tab === 'uo' && (
            <div className="space-y-3">
              <p className="text-sm text-slate-600">
                Seleziona le Unità Organizzative a cui l&apos;utente appartiene. L&apos;utente vedrà documenti,
                fascicoli e protocolli di tutte le UO selezionate.
              </p>
              <input
                type="text"
                placeholder="🔍 Cerca UO..."
                value={ouSearching}
                onChange={(e) => setOuSearching(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
              />
              <div className="max-h-72 overflow-y-auto rounded border border-slate-200">
                {allOUs
                  .filter(
                    (ou) =>
                      !ouSearching.trim() ||
                      ou.name.toLowerCase().includes(ouSearching.toLowerCase()) ||
                      ou.code.toLowerCase().includes(ouSearching.toLowerCase()),
                  )
                  .map((ou) => {
                    const isMember = userOUIds.has(ou.id)
                    return (
                      <label
                        key={ou.id}
                        className={`flex cursor-pointer items-center gap-3 border-b border-slate-100 px-3 py-2.5 hover:bg-slate-50 ${
                          isMember ? 'bg-indigo-50/50' : ''
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isMember}
                          onChange={() => handleToggleOU(ou.id)}
                          disabled={ouLoading}
                          className="rounded"
                        />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-slate-800">🏢 {ou.name}</p>
                          <p className="text-xs text-slate-500">Codice: {ou.code}</p>
                        </div>
                        {isMember && (
                          <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700">Membro</span>
                        )}
                      </label>
                    )
                  })}
              </div>
              <p className="text-xs text-slate-400">
                {userOUIds.size} UO assegnate — le modifiche sono immediate
              </p>
            </div>
          )}

          {tab === 'groups' && (
            <div className="space-y-3">
              <p className="text-sm text-slate-600">
                Seleziona i gruppi a cui l&apos;utente appartiene. I gruppi sono organizzati per UO.
              </p>
              <input
                type="text"
                placeholder="🔍 Cerca gruppo..."
                value={groupSearching}
                onChange={(e) => setGroupSearching(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
              />
              {allGroups.length === 0 ? (
                <p className="py-4 text-center text-sm text-slate-400">
                  Nessun gruppo disponibile. Crea gruppi dalla sezione Organizzazioni.
                </p>
              ) : (
                <div className="max-h-72 overflow-y-auto rounded border border-slate-200">
                  {allGroups
                    .filter(
                      (g) =>
                        !groupSearching.trim() || g.name.toLowerCase().includes(groupSearching.toLowerCase()),
                    )
                    .map((g) => {
                      const isMember = userGroupIds.has(g.id)
                      return (
                        <label
                          key={g.id}
                          className={`flex cursor-pointer items-center gap-3 border-b border-slate-100 px-3 py-2.5 hover:bg-slate-50 ${
                            isMember ? 'bg-indigo-50/50' : ''
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isMember}
                            onChange={() => handleToggleGroup(g.id)}
                            disabled={groupsLoading}
                            className="rounded"
                          />
                          <div className="flex-1">
                            <p className="text-sm font-medium text-slate-800">📂 {g.name}</p>
                            <p className="text-xs text-slate-500">
                              {g.organizational_unit_name ? `UO: ${g.organizational_unit_name}` : 'Senza UO'}
                              {' · '}
                              {g.members_count} membri
                            </p>
                          </div>
                          {isMember && (
                            <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700">Membro</span>
                          )}
                        </label>
                      )
                    })}
                </div>
              )}
              <p className="text-xs text-slate-400">
                {userGroupIds.size} gruppi assegnati — le modifiche sono immediate
              </p>
            </div>
          )}

          {tab === 'permissions' && (
            <div className="space-y-4">
              <p className="text-sm text-slate-600">
                <span className="font-medium text-green-600">Verde</span> = accesso via UO.
                <span className="ml-1 font-medium text-blue-600">Blu</span> = accesso esplicito. Espandi le
                cartelle per vedere i file. Usa la ricerca per trovare elementi specifici.
              </p>

              <input
                type="text"
                placeholder="🔍 Cerca documento o fascicolo..."
                value={permDocSearch}
                onChange={(e) => setPermDocSearch(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
              />

              {(() => {
                const searchTerm = permDocSearch.trim().toLowerCase()
                const permDocIds = new Set((userPerms?.documents ?? []).map((d) => d.document_id))
                const permDossierIds = new Set((userPerms?.dossiers ?? []).map((d) => d.dossier_id))

                type FolderGroup = { id: string | null; name: string; docs: DocumentItem[] }
                const folderMap = new Map<string | null, FolderGroup>()
                allDocs.forEach((doc) => {
                  const folderId = doc.folder_id ?? doc.folder ?? null
                  const folderName = doc.folder_name ?? null
                  const existingGroup = folderMap.get(folderId)
                  if (
                    existingGroup &&
                    folderName &&
                    existingGroup.name === 'Cartella sconosciuta'
                  ) {
                    existingGroup.name = folderName
                  }
                  if (!folderMap.has(folderId)) {
                    folderMap.set(folderId, {
                      id: folderId,
                      name: folderName || (folderId ? 'Cartella sconosciuta' : 'Documenti generali'),
                      docs: [],
                    })
                  }
                  folderMap.get(folderId)!.docs.push(doc)
                })
                const groups = Array.from(folderMap.values())

                const isSearching = searchTerm.length > 0

                const filteredGroups = groups
                  .map((g) => ({
                    ...g,
                    docs: isSearching
                      ? g.docs.filter((d) => d.title.toLowerCase().includes(searchTerm))
                      : g.docs,
                  }))
                  .filter((g) => g.docs.length > 0)

                const filteredDossiers = allDossiers.filter(
                  (d) =>
                    !isSearching ||
                    d.title.toLowerCase().includes(searchTerm) ||
                    (d.identifier || '').toLowerCase().includes(searchTerm),
                )

                return (
                  <>
                    <div>
                      <h3 className="mb-1 flex items-center gap-2 text-sm font-semibold text-slate-700">
                        📄 Documenti{' '}
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                          {allDocs.length}
                        </span>
                      </h3>
                      <div className="overflow-hidden rounded border border-slate-200">
                        {filteredGroups.map((group) => (
                          <PermissionFolder
                            key={group.id ?? 'root'}
                            name={group.name}
                            count={group.docs.length}
                            defaultOpen={isSearching}
                          >
                            {group.docs.map((doc) => {
                              const hasExplicit = permDocIds.has(doc.id)
                              const docPerm = (userPerms?.documents ?? []).find(
                                (d) => d.document_id === doc.id,
                              )
                              return (
                                <div
                                  key={doc.id}
                                  className={`flex items-center justify-between border-b border-slate-100 px-3 py-1.5 pl-8 hover:bg-slate-50 ${
                                    hasExplicit ? 'bg-blue-50/30' : ''
                                  }`}
                                >
                                  <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2">
                                    <input
                                      type="checkbox"
                                      checked={hasExplicit}
                                      onChange={() =>
                                        hasExplicit
                                          ? void handleRemoveDocPermission(doc.id)
                                          : void handleAddDocPermission(doc.id)
                                      }
                                      disabled={addingPerm}
                                      className="rounded"
                                    />
                                    <span className="truncate text-sm text-slate-800">{doc.title}</span>
                                  </label>
                                  {hasExplicit && (
                                    <div className="ml-2 flex shrink-0 items-center gap-1">
                                      <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">
                                        Esplicito
                                      </span>
                                      <button
                                        type="button"
                                        onClick={() =>
                                          void handleToggleDocWrite(doc.id, docPerm?.can_write ?? false)
                                        }
                                        className={`rounded px-1.5 py-0.5 text-xs ${
                                          docPerm?.can_write
                                            ? 'bg-amber-100 font-medium text-amber-700'
                                            : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
                                        }`}
                                      >
                                        {docPerm?.can_write ? '✏️ R/W' : '👁 R'}
                                      </button>
                                    </div>
                                  )}
                                </div>
                              )
                            })}
                          </PermissionFolder>
                        ))}
                        {filteredGroups.length === 0 && (
                          <p className="px-3 py-3 text-center text-sm text-slate-400">
                            {isSearching ? 'Nessun documento trovato.' : 'Nessun documento nel sistema.'}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="rounded border border-slate-200 overflow-hidden">
                      <PermissionFolder
                        name="Fascicoli"
                        count={filteredDossiers.length}
                        defaultOpen={isSearching}
                      >
                        {filteredDossiers.length > 0 ? (
                          filteredDossiers.map((dossier) => {
                            const hasExplicit = permDossierIds.has(dossier.id)
                            const dossierPerm = (userPerms?.dossiers ?? []).find(
                              (d) => d.dossier_id === dossier.id,
                            )
                            const ouId = (
                              dossier as DossierItem & { organizational_unit?: string | null }
                            ).organizational_unit
                            const isInUserOU = Boolean(ouId && userOUIds.has(ouId))
                            return (
                              <div
                                key={dossier.id}
                                className={`flex items-center justify-between border-b border-slate-100 px-3 py-2 pl-8 hover:bg-slate-50 ${
                                  hasExplicit ? 'bg-blue-50/30' : isInUserOU ? 'bg-green-50/30' : ''
                                }`}
                              >
                                <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2">
                                  <input
                                    type="checkbox"
                                    checked={hasExplicit}
                                    onChange={() =>
                                      hasExplicit
                                        ? void handleRemoveDossierPermission(dossier.id)
                                        : void handleAddDossierPermission(dossier.id)
                                    }
                                    disabled={addingPerm}
                                    className="rounded"
                                  />
                                  <div className="min-w-0">
                                    <span className="block truncate text-sm text-slate-800">
                                      {dossier.title}
                                    </span>
                                    <span className="font-mono text-xs text-slate-500">
                                      {dossier.identifier}
                                    </span>
                                  </div>
                                </label>
                                <div className="ml-2 flex shrink-0 items-center gap-1">
                                  {isInUserOU && (
                                    <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700">
                                      UO
                                    </span>
                                  )}
                                  {hasExplicit && (
                                    <>
                                      <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">
                                        Esplicito
                                      </span>
                                      <button
                                        type="button"
                                        onClick={() =>
                                          void handleToggleDossierWrite(
                                            dossier.id,
                                            dossierPerm?.can_write ?? false,
                                          )
                                        }
                                        className={`rounded px-1.5 py-0.5 text-xs ${
                                          dossierPerm?.can_write
                                            ? 'bg-amber-100 font-medium text-amber-700'
                                            : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
                                        }`}
                                      >
                                        {dossierPerm?.can_write ? '✏️ R/W' : '👁 R'}
                                      </button>
                                    </>
                                  )}
                                  {!isInUserOU && !hasExplicit && (
                                    <span className="text-xs text-slate-300">Nessun accesso</span>
                                  )}
                                </div>
                              </div>
                            )
                          })
                        ) : (
                          <p className="px-3 py-3 pl-8 text-center text-sm text-slate-400">
                            {isSearching ? 'Nessun fascicolo trovato.' : 'Nessun fascicolo.'}
                          </p>
                        )}
                      </PermissionFolder>
                    </div>

                    <div className="rounded border border-slate-200 overflow-hidden">
                      <PermissionFolder name="Archivi" count={0} defaultOpen={false}>
                        <p className="px-3 py-4 pl-8 text-center text-sm text-slate-400">
                          Nessun archivio presente. Gli archivi appariranno qui quando verranno creati.
                        </p>
                      </PermissionFolder>
                    </div>

                    <div className="flex flex-wrap gap-3 rounded bg-slate-50 px-3 py-2 text-xs">
                      <span className="flex items-center gap-1">
                        <span className="inline-block h-3 w-3 rounded border border-green-300 bg-green-100" />
                        Via UO
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="inline-block h-3 w-3 rounded border border-blue-300 bg-blue-100" />
                        Esplicito
                      </span>
                      <span>👁 R = Lettura</span>
                      <span>✏️ R/W = Lettura + Scrittura</span>
                    </div>
                  </>
                )
              })()}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 px-6 py-3">
          <p className="text-xs text-slate-400">
            Le modifiche a UO, Gruppi e Permessi accesso sono salvate automaticamente
          </p>
          <button
            type="button"
            onClick={onClose}
            className="rounded bg-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-300"
          >
            Chiudi
          </button>
        </div>
      </div>
    </div>
  )
}
