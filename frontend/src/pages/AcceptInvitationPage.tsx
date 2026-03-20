import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, setTokens } from '../services/api'
import { useAuthStore } from '../store/authStore'
import type { User } from '../types/auth'

const schema = z
  .object({
    first_name: z.string().min(1, 'Obbligatorio'),
    last_name: z.string().min(1, 'Obbligatorio'),
    password: z.string().min(8, 'Minimo 8 caratteri').regex(/[A-Z]/, 'Almeno una maiuscola').regex(/\d/, 'Almeno un numero'),
    password_confirm: z.string(),
  })
  .refine((d) => d.password === d.password_confirm, {
    message: 'Le password non coincidono',
    path: ['password_confirm'],
  })

type FormData = z.infer<typeof schema>

export function AcceptInvitationPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const setUser = useAuthStore((s) => s.setUser)
  const [email, setEmail] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    api
      .get(`/api/auth/accept-invitation/${token}/`)
      .then((r) => setEmail(r.data.email))
      .catch(() => setError('Invito non valido o scaduto.'))
      .finally(() => setLoading(false))
  }, [token])

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { first_name: '', last_name: '', password: '', password_confirm: '' },
  })

  const onSubmit = async (data: FormData) => {
    if (!token) return
    setError(null)
    try {
      const res = await api.post<{ access: string; refresh: string; user: User }>(
        `/api/auth/accept-invitation/${token}/`,
        {
          first_name: data.first_name,
          last_name: data.last_name,
          password: data.password,
          password_confirm: data.password_confirm,
        }
      )
      setTokens(res.data.access, res.data.refresh)
      setUser(res.data.user)
      navigate('/dashboard')
    } catch (err: unknown) {
      const r = (err as { response?: { data?: { detail?: string } } })?.response
      setError(r?.data?.detail ?? 'Errore durante l\'accettazione.')
    }
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
        <div className="rounded-lg bg-white p-8 shadow-md">
          <p className="text-red-600">Link non valido.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
        <div className="text-slate-600">Caricamento...</div>
      </div>
    )
  }

  if (error && !email) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
        <div className="rounded-lg bg-white p-8 shadow-md">
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
        <h1 className="text-xl font-bold text-slate-800">Accetta invito</h1>
        <p className="mb-4 text-slate-600">Completa la registrazione per {email}</p>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Nome</label>
            <input
              className="w-full rounded border border-slate-300 px-3 py-2"
              {...register('first_name')}
            />
            {errors.first_name && (
              <p className="mt-1 text-sm text-red-600">{errors.first_name.message}</p>
            )}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Cognome</label>
            <input
              className="w-full rounded border border-slate-300 px-3 py-2"
              {...register('last_name')}
            />
            {errors.last_name && (
              <p className="mt-1 text-sm text-red-600">{errors.last_name.message}</p>
            )}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Password</label>
            <input
              type="password"
              className="w-full rounded border border-slate-300 px-3 py-2"
              {...register('password')}
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
            )}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Conferma password</label>
            <input
              type="password"
              className="w-full rounded border border-slate-300 px-3 py-2"
              {...register('password_confirm')}
            />
            {errors.password_confirm && (
              <p className="mt-1 text-sm text-red-600">{errors.password_confirm.message}</p>
            )}
          </div>
          {error && (
            <div className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</div>
          )}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded bg-indigo-600 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {isSubmitting ? 'Registrazione...' : 'Accetta e accedi'}
          </button>
        </form>
      </div>
    </div>
  )
}
