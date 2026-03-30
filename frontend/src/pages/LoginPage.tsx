import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { login } from '../services/authService'
import type { LoginResponse } from '../types/auth'
import { MFAVerifyModal } from '../components/auth/MFAVerifyModal'
import { SSOButtons } from '../components/auth/SSOButtons'
const loginSchema = z.object({
  email: z.string().email('Email non valida'),
  password: z.string().min(6, 'Minimo 6 caratteri'),
})

type LoginForm = z.infer<typeof loginSchema>

export function LoginPage() {
  const navigate = useNavigate()
  const setUser = useAuthStore((s) => s.setUser)
  const [error, setError] = useState<string | null>(null)
  const [lockedUntil, setLockedUntil] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [mfaPendingToken, setMfaPendingToken] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  const onSubmit = async (data: LoginForm) => {
    setError(null)
    setLockedUntil(null)
    setMfaPendingToken(null)
    setIsSubmitting(true)
    try {
      const res = await login(data.email, data.password)
      if ('mfa_required' in res && res.mfa_required) {
        setMfaPendingToken(res.mfa_pending_token)
        return
      }
      const loginRes = res as LoginResponse
      setUser(loginRes.user)
      navigate('/dashboard')
    } catch (err: unknown) {
      const res = (err as { response?: { status: number; data?: unknown } })?.response
      if (res?.status === 423) {
        const data = res.data as { locked_until?: string; message?: string }
        setLockedUntil(data?.locked_until ?? null)
        setError(data?.message ?? 'Account bloccato. Riprova dopo qualche minuto.')
      } else if (res?.status === 401) {
        setError('Email o password non corretti.')
      } else {
        setError('Errore di connessione. Riprova.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-slate-100 p-4 dark:bg-slate-900">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-8 shadow-md dark:border-slate-700 dark:bg-slate-800">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">AXDOC</h1>
        <p className="mb-6 text-slate-600 dark:text-slate-300">Gestione Documentale</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
              {...register('email')}
            />
            {errors.email && (
              <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
            )}
          </div>
          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
              {...register('password')}
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
            )}
          </div>
          {error && (
            <div className="rounded bg-red-50 p-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
              {error}
              {lockedUntil && (
                <p className="mt-1 text-xs">
                  Sblocco previsto: {new Date(lockedUntil).toLocaleString('it-IT')}
                </p>
              )}
            </div>
          )}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded bg-indigo-600 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {isSubmitting ? 'Accesso in corso...' : 'Accedi'}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-600 dark:text-slate-400">
          <Link to="/forgot-password" className="text-indigo-600 hover:underline dark:text-indigo-400">
            Hai dimenticato la password?
          </Link>
        </p>
        <SSOButtons />
      </div>
      <MFAVerifyModal
        open={!!mfaPendingToken}
        mfaPendingToken={mfaPendingToken ?? ''}
        onSuccess={(user) => {
          setUser(user)
          setMfaPendingToken(null)
          // La modale per cambio password obbligatorio apparirà automaticamente in App.tsx se necessario
          navigate('/dashboard')
        }}
        onClose={() => setMfaPendingToken(null)}
      />
    </div>
  )
}
