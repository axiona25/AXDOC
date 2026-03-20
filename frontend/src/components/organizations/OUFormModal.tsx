import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import type { OrganizationalUnit } from '../../services/organizationService'

const schema = z.object({
  name: z.string().min(1, 'Obbligatorio'),
  code: z.string().min(1, 'Codice obbligatorio').max(50),
  description: z.string().optional(),
  parent: z.string().uuid().optional().or(z.literal('')),
})

type FormData = z.infer<typeof schema>

interface OUFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: { name: string; code: string; description?: string; parent?: string | null }) => Promise<void>
  initial?: OrganizationalUnit | null
  organizations: OrganizationalUnit[]
}

export function OUFormModal({
  isOpen,
  onClose,
  onSubmit,
  initial,
  organizations,
}: OUFormModalProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: initial?.name ?? '',
      code: initial?.code ?? '',
      description: initial?.description ?? '',
      parent: initial?.parent ?? '',
    },
  })

  const submit = async (data: FormData) => {
    await onSubmit({
      name: data.name,
      code: data.code,
      description: data.description || undefined,
      parent: data.parent || null,
    })
    reset()
    onClose()
  }

  if (!isOpen) return null

  const rootOrgs = organizations.filter((o) => !o.parent)
  const parentOptions = initial
    ? rootOrgs.filter((o) => o.id !== initial.id)
    : rootOrgs

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">
          {initial ? 'Modifica unità organizzativa' : 'Nuova unità organizzativa'}
        </h2>
        <form onSubmit={handleSubmit(submit)} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Nome</label>
            <input
              className="w-full rounded border border-slate-300 px-3 py-2"
              {...register('name')}
            />
            {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Codice (univoco)</label>
            <input
              className="w-full rounded border border-slate-300 px-3 py-2"
              {...register('code')}
              disabled={!!initial}
            />
            {errors.code && <p className="mt-1 text-sm text-red-600">{errors.code.message}</p>}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Descrizione</label>
            <textarea
              className="w-full rounded border border-slate-300 px-3 py-2"
              rows={2}
              {...register('description')}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Parent</label>
            <select className="w-full rounded border border-slate-300 px-3 py-2" {...register('parent')}>
              <option value="">Nessuna (radice)</option>
              {parentOptions.map((o) => (
                <option key={o.id} value={o.id}>{o.code} — {o.name}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded border border-slate-300 px-4 py-2">
              Annulla
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {initial ? 'Salva' : 'Crea'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
