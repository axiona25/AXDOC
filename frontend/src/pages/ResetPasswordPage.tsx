import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { confirmPasswordReset } from '../services/authService'

const schema = z
  .object({
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

export function ResetPasswordPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { new_password: '', new_password_confirm: '' },
  })

  const onSubmit = async (data: FormData) => {
    if (!token) return
    setError(null)
    try {
      await confirmPasswordReset(
        token,
        data.new_password,
        data.new_password_confirm
      )
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch {
      setError('Link non valido o scaduto.')
    }
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
        <div className="rounded-lg bg-white p-8 shadow-md">
          <p className="text-red-600">Link non valido.</p>
          <Link to="/login" className="mt-4 inline-block text-indigo-600 hover:underline">
            Torna al login
          </Link>
        </div>
      </div>
    )
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
        <div className="rounded-lg bg-white p-8 shadow-md">
          <p className="text-green-700">Password cambiata. Reindirizzamento al login...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
        <h1 className="text-xl font-bold text-slate-800">Nuova password</h1>
        <p className="mb-6 text-slate-600">Inserisci la nuova password.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
              Conferma password
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
        <p className="mt-4 text-center text-sm text-slate-600">
          <Link to="/login" className="text-indigo-600 hover:underline">
            Torna al login
          </Link>
        </p>
      </div>
    </div>
  )
}
