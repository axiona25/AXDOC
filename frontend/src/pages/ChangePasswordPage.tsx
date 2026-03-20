import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { changePassword } from '../services/authService'

const schema = z
  .object({
    old_password: z.string().min(1, 'Obbligatorio'),
    new_password: z
      .string()
      .min(8, 'Minimo 8 caratteri')
      .regex(/[A-Z]/, 'Almeno una maiuscola')
      .regex(/\d/, 'Almeno un numero'),
    new_password_confirm: z.string(),
  })
  .refine((data) => data.new_password === data.new_password_confirm, {
    message: 'Le password non coincidono',
    path: ['new_password_confirm'],
  })

type FormData = z.infer<typeof schema>

export function ChangePasswordPage() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { old_password: '', new_password: '', new_password_confirm: '' },
  })

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      await changePassword(
        data.old_password,
        data.new_password,
        data.new_password_confirm
      )
      navigate('/dashboard')
    } catch (err: unknown) {
      const res = (err as { response?: { data?: { old_password?: string[] } } })?.response
      const msg = res?.data?.old_password?.[0] ?? 'Errore durante il cambio password.'
      setError(msg)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
        <h1 className="text-xl font-bold text-slate-800">Cambio password</h1>
        <p className="mb-6 text-slate-600">Inserisci la password attuale e la nuova.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label htmlFor="old_password" className="mb-1 block text-sm font-medium text-slate-700">
              Password attuale
            </label>
            <input
              id="old_password"
              type="password"
              autoComplete="current-password"
              className="w-full rounded border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              {...register('old_password')}
            />
            {errors.old_password && (
              <p className="mt-1 text-sm text-red-600">{errors.old_password.message}</p>
            )}
          </div>
          <div>
            <label htmlFor="new_password" className="mb-1 block text-sm font-medium text-slate-700">
              Nuova password
            </label>
            <input
              id="new_password"
              type="password"
              autoComplete="new-password"
              className="w-full rounded border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              {...register('new_password')}
            />
            {errors.new_password && (
              <p className="mt-1 text-sm text-red-600">{errors.new_password.message}</p>
            )}
          </div>
          <div>
            <label htmlFor="new_password_confirm" className="mb-1 block text-sm font-medium text-slate-700">
              Conferma nuova password
            </label>
            <input
              id="new_password_confirm"
              type="password"
              autoComplete="new-password"
              className="w-full rounded border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              {...register('new_password_confirm')}
            />
            {errors.new_password_confirm && (
              <p className="mt-1 text-sm text-red-600">{errors.new_password_confirm.message}</p>
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
            {isSubmitting ? 'Salvataggio...' : 'Salva password'}
          </button>
        </form>
      </div>
    </div>
  )
}
