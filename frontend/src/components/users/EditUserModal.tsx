import { useState, useEffect } from 'react'
import type { User } from '../../types/auth'
import { updateUser, type UpdateUserData } from '../../services/userService'
import type { OrganizationalUnit } from '../../services/organizationService'

const ROLE_LABELS: Record<string, string> = {
  OPERATOR: 'Operatore',
  REVIEWER: 'Revisore',
  APPROVER: 'Approvatore',
  ADMIN: 'Amministratore',
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
  organizations = [],
}: EditUserModalProps) {
  const [first_name, setFirst_name] = useState('')
  const [last_name, setLast_name] = useState('')
  const [role, setRole] = useState<string>('OPERATOR')
  const [user_type, setUser_type] = useState<'internal' | 'guest'>('internal')
  const [is_active, setIs_active] = useState(true)
  const [selectedOuId, setSelectedOuId] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (user) {
      setFirst_name(user.first_name ?? '')
      setLast_name(user.last_name ?? '')
      setRole(user.role ?? 'OPERATOR')
      setUser_type((user.user_type as 'internal' | 'guest') ?? 'internal')
      setIs_active(user.is_active ?? true)
      setSelectedOuId(user?.organizational_unit?.id ?? '')
      setErrors({})
    }
  }, [user, isOpen])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!user) return
    setErrors({})
    const nameTrimmed = first_name.trim()
    const surnameTrimmed = last_name.trim()
    if (!nameTrimmed) {
      setErrors((prev) => ({ ...prev, first_name: 'Nome obbligatorio.' }))
      return
    }
    if (!surnameTrimmed) {
      setErrors((prev) => ({ ...prev, last_name: 'Cognome obbligatorio.' }))
      return
    }
    setLoading(true)
    try {
      const payload: UpdateUserData = {
        first_name: nameTrimmed,
        last_name: surnameTrimmed,
        role,
        user_type,
        is_active,
        organizational_unit_id: selectedOuId || null,
      }
      await updateUser(user.id, payload)
      onSuccess()
      onClose()
    } catch (err: unknown) {
      const res = (err as { response?: { data?: Record<string, string | string[]> } })?.response?.data
      if (res && typeof res === 'object') {
        const next: Record<string, string> = {}
        for (const [k, v] of Object.entries(res)) {
          next[k] = Array.isArray(v) ? v[0] : String(v)
        }
        setErrors(next)
      } else {
        setErrors({ _form: 'Errore durante il salvataggio.' })
      }
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-labelledby="edit-user-title">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
        <h2 id="edit-user-title" className="mb-4 text-lg font-semibold text-slate-800">
          Modifica utente
        </h2>
        {user && (
          <p className="mb-3 text-sm text-slate-500">{user.email}</p>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          {errors._form && (
            <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
              {errors._form}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="edit-first_name" className="mb-1 block text-sm font-medium text-slate-700">Nome *</label>
              <input
                id="edit-first_name"
                type="text"
                value={first_name}
                onChange={(e) => setFirst_name(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
              {errors.first_name && <p className="mt-1 text-xs text-red-600">{errors.first_name}</p>}
            </div>
            <div>
              <label htmlFor="edit-last_name" className="mb-1 block text-sm font-medium text-slate-700">Cognome *</label>
              <input
                id="edit-last_name"
                type="text"
                value={last_name}
                onChange={(e) => setLast_name(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
              {errors.last_name && <p className="mt-1 text-xs text-red-600">{errors.last_name}</p>}
            </div>
          </div>
          <div>
            <label htmlFor="edit-role" className="mb-1 block text-sm font-medium text-slate-700">Ruolo *</label>
            <select
              id="edit-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              disabled={user_type === 'guest'}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-500"
            >
              {Object.entries(ROLE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            {errors.role && <p className="mt-1 text-xs text-red-600">{errors.role}</p>}
          </div>
          <div>
            <span className="mb-2 block text-sm font-medium text-slate-700">Tipo utente *</span>
            <div className="flex gap-4">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="edit-user_type"
                  checked={user_type === 'internal'}
                  onChange={() => setUser_type('internal')}
                />
                <span className="text-sm">Interno</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="edit-user_type"
                  checked={user_type === 'guest'}
                  onChange={() => {
                    setUser_type('guest')
                    setRole('OPERATOR')
                  }}
                />
                <span className="text-sm">Ospite</span>
              </label>
            </div>
            {errors.user_type && <p className="mt-1 text-xs text-red-600">{errors.user_type}</p>}
          </div>
          <div>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={is_active}
                onChange={(e) => setIs_active(e.target.checked)}
                className="rounded border-slate-300"
              />
              <span className="text-sm font-medium text-slate-700">Attivo</span>
            </label>
            {errors.is_active && <p className="mt-1 text-xs text-red-600">{errors.is_active}</p>}
          </div>
          <div>
            <label htmlFor="edit-ou" className="mb-1 block text-sm font-medium text-slate-700">Unità organizzativa</label>
            <select
              id="edit-ou"
              value={selectedOuId}
              onChange={(e) => setSelectedOuId(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">— Nessuna —</option>
              {organizations.map((ou) => (
                <option key={ou.id} value={ou.id}>{ou.code} — {ou.name}</option>
              ))}
            </select>
            {errors.organizational_unit_id && <p className="mt-1 text-xs text-red-600">{errors.organizational_unit_id}</p>}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? 'Salvataggio...' : 'Salva'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
