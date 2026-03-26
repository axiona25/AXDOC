import { useState, useCallback } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useModalEscape } from '../../hooks/useModalAccessibility'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { inviteUser, type InviteUserData } from '../../services/userService'
import type { OrganizationalUnit } from '../../services/organizationService'

const schema = z.object({
  email: z.string().email('Email non valida'),
  role: z.string().min(1),
  organizational_unit_id: z.string().uuid().optional().or(z.literal('')),
  ou_role: z.string().optional(),
})

type FormData = z.infer<typeof schema>

interface InviteUserModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  organizations: OrganizationalUnit[]
}

export function InviteUserModal({
  isOpen,
  onClose,
  onSuccess,
  organizations,
}: InviteUserModalProps) {
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: '',
      role: 'OPERATOR',
      organizational_unit_id: '',
      ou_role: 'OPERATOR',
    },
  })

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      const payload: InviteUserData = {
        email: data.email,
        role: data.role,
        ou_role: data.ou_role || 'OPERATOR',
      }
      if (data.organizational_unit_id) {
        payload.organizational_unit_id = data.organizational_unit_id
      }
      await inviteUser(payload)
      reset()
      onSuccess()
      onClose()
    } catch (err: unknown) {
      const res = (err as { response?: { data?: { email?: string[] } } })?.response
      setError(res?.data?.email?.[0] ?? 'Errore durante l\'invio dell\'invito.')
    }
  }

  const modalRef = useFocusTrap(isOpen)
  const closeCb = useCallback(() => onClose(), [onClose])
  useModalEscape(isOpen, closeCb)

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title-invite-user"
        className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <h2 id="modal-title-invite-user" className="mb-4 text-lg font-semibold text-slate-800">
          Invita utente
        </h2>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Email</label>
            <input
              type="email"
              className="w-full rounded border border-slate-300 px-3 py-2"
              {...register('email')}
            />
            {errors.email && (
              <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
            )}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Ruolo</label>
            <select className="w-full rounded border border-slate-300 px-3 py-2" {...register('role')}>
              <option value="OPERATOR">Operatore</option>
              <option value="REVIEWER">Revisore</option>
              <option value="APPROVER">Approvatore</option>
              <option value="ADMIN">Amministratore</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Unità organizzativa</label>
            <select
              className="w-full rounded border border-slate-300 px-3 py-2"
              {...register('organizational_unit_id')}
            >
              <option value="">Nessuna</option>
              {organizations.map((ou) => (
                <option key={ou.id} value={ou.id}>
                  {ou.code} — {ou.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Ruolo nella U.O.</label>
            <select className="w-full rounded border border-slate-300 px-3 py-2" {...register('ou_role')}>
              <option value="OPERATOR">Operatore</option>
              <option value="REVIEWER">Revisore</option>
              <option value="APPROVER">Approvatore</option>
            </select>
          </div>
          {error && (
            <div className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</div>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-slate-300 px-4 py-2 text-slate-700"
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Invio...' : 'Invia invito'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
