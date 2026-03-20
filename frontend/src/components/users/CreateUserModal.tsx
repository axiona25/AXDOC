import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Dialog, DialogTitle } from '@headlessui/react'
import { createUserManual, type CreateUserManualData } from '../../services/userService'
import type { OrganizationalUnit } from '../../services/organizationService'

const schema = z.object({
  email: z.string().email('Email non valida'),
  first_name: z.string().min(1, 'Nome obbligatorio'),
  last_name: z.string().min(1, 'Cognome obbligatorio'),
  user_type: z.enum(['internal', 'guest']),
  role: z.string().optional(),
  organizational_unit_id: z.string().uuid().optional().or(z.literal('')),
  password: z.string().optional(),
  generate_password: z.boolean().optional(),
  send_welcome_email: z.boolean().optional(),
})

type FormData = z.infer<typeof schema>

interface CreateUserModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  organizations: OrganizationalUnit[]
}

const ROLE_LABELS: Record<string, string> = {
  OPERATOR: 'Operatore',
  REVIEWER: 'Revisore',
  APPROVER: 'Approvatore',
  ADMIN: 'Amministratore',
}

export function CreateUserModal({
  isOpen,
  onClose,
  onSuccess,
  organizations,
}: CreateUserModalProps) {
  const [error, setError] = useState<string | null>(null)
  const [successData, setSuccessData] = useState<{
    email: string
    generated_password: string
  } | null>(null)
  const {
    register,
    handleSubmit,
    watch,
    reset,
    setError: setFieldError,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: '',
      first_name: '',
      last_name: '',
      user_type: 'internal',
      role: 'OPERATOR',
      organizational_unit_id: '',
      password: '',
      generate_password: true,
      send_welcome_email: true,
    },
  })

  const userType = watch('user_type')
  const generatePassword = watch('generate_password')

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      const payload: CreateUserManualData = {
        email: data.email,
        first_name: data.first_name,
        last_name: data.last_name,
        user_type: data.user_type,
        send_welcome_email: data.send_welcome_email ?? true,
      }
      if (data.user_type === 'internal') {
        payload.role = data.role || 'OPERATOR'
        if (data.organizational_unit_id) payload.organizational_unit_id = data.organizational_unit_id
      }
      if (!data.generate_password && data.password?.trim()) payload.password = data.password.trim()
      const response = await createUserManual(payload)
      
      // Se c'è una password generata, mostra il modal di successo
      if (response.generated_password) {
        setSuccessData({
          email: response.user.email,
          generated_password: response.generated_password,
        })
      } else {
        // Se non c'è password generata, chiudi normalmente
        reset()
        onSuccess()
        onClose()
      }
    } catch (err: unknown) {
      const res = (err as { response?: { data?: { detail?: string; email?: string[]; non_field_errors?: string[] } } })?.response
      const errorData = res?.data
      
      // Se c'è un errore email, mostralo sotto il campo email
      if (errorData?.email) {
        setFieldError('email', {
          type: 'server',
          message: Array.isArray(errorData.email) ? errorData.email[0] : errorData.email,
        })
      }
      // Se ci sono errori generali (non_field_errors o detail), mostra banner rosso
      else if (errorData?.non_field_errors || errorData?.detail) {
        const errorMessage = Array.isArray(errorData.non_field_errors) 
          ? errorData.non_field_errors[0] 
          : errorData.detail || 'Errore durante la creazione.'
        setError(errorMessage)
      } else {
        setError('Errore durante la creazione.')
      }
    }
  }

  const handleCopyPassword = () => {
    if (successData?.generated_password) {
      navigator.clipboard.writeText(successData.generated_password)
    }
  }

  const handleCloseSuccess = () => {
    setSuccessData(null)
    reset()
    onSuccess()
    onClose()
  }

  if (!isOpen) return null

  return (
    <>
      {/* Modal di successo con password generata */}
      <Dialog open={!!successData} onClose={() => {}} className="relative z-[60]">
        <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="mx-auto w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <DialogTitle className="text-lg font-semibold text-slate-800">
              Utente creato con successo!
            </DialogTitle>
            <div className="mt-4 space-y-3">
              <div>
                <p className="text-sm text-slate-600">
                  <span className="font-medium">Email:</span> {successData?.email}
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-600">
                  <span className="font-medium">Password temporanea:</span>
                </p>
                <div className="mt-1 flex items-center gap-2">
                  <code className="flex-1 rounded bg-slate-100 px-3 py-2 text-sm font-mono">
                    {successData?.generated_password}
                  </code>
                  <button
                    type="button"
                    onClick={handleCopyPassword}
                    className="rounded border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                  >
                    Copia password
                  </button>
                </div>
              </div>
              <p className="text-xs text-slate-500">
                L&apos;utente dovrà cambiarla al primo accesso.
              </p>
            </div>
            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={handleCloseSuccess}
                className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
              >
                Chiudi
              </button>
            </div>
          </Dialog.Panel>
        </div>
      </Dialog>

      {/* Modal di creazione utente */}
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Nuovo utente</h2>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Email *</label>
            <input
              type="email"
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              {...register('email')}
            />
            {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Nome *</label>
            <input
              type="text"
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              {...register('first_name')}
            />
            {errors.first_name && <p className="mt-1 text-xs text-red-600">{errors.first_name.message}</p>}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Cognome *</label>
            <input
              type="text"
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              {...register('last_name')}
            />
            {errors.last_name && <p className="mt-1 text-xs text-red-600">{errors.last_name.message}</p>}
          </div>

          <div>
            <span className="mb-2 block text-sm font-medium text-slate-700">Tipo utente *</span>
            <div className="flex gap-4">
              <label className="flex items-center gap-2">
                <input type="radio" value="internal" {...register('user_type')} />
                <span className="text-sm">Interno</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="radio" value="guest" {...register('user_type')} />
                <span className="text-sm">Ospite</span>
              </label>
            </div>
          </div>

          {userType === 'internal' && (
            <>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Ruolo *</label>
                <select
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  {...register('role')}
                >
                  {Object.entries(ROLE_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Unità organizzativa</label>
                <select
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  {...register('organizational_unit_id')}
                >
                  <option value="">— Nessuna —</option>
                  {organizations.map((ou) => (
                    <option key={ou.id} value={ou.id}>{ou.name}</option>
                  ))}
                </select>
              </div>
            </>
          )}

          <div>
            <label className="flex items-center gap-2">
              <input type="checkbox" {...register('generate_password')} />
              <span className="text-sm font-medium text-slate-700">Genera password automaticamente</span>
            </label>
          </div>
          {!generatePassword && (
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Password</label>
              <input
                type="password"
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                placeholder="Min 8 caratteri, 1 maiuscola, 1 numero"
                {...register('password')}
              />
              {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
            </div>
          )}

          <div>
            <label className="flex items-center gap-2">
              <input type="checkbox" {...register('send_welcome_email')} />
              <span className="text-sm font-medium text-slate-700">Invia email di benvenuto</span>
            </label>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Creazione...' : 'Crea utente'}
            </button>
          </div>
        </form>
      </div>
    </div>
    </>
  )
}
