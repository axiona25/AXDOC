import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { setTokens } from '../services/api'
import { useAuthStore } from '../store/authStore'
import { getMe } from '../services/authService'

export function SSOCallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const setUser = useAuthStore((s) => s.setUser)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const access = searchParams.get('access')
    const refresh = searchParams.get('refresh')
    const err = searchParams.get('error')

    if (err) {
      setError(err)
      setLoading(false)
      return
    }
    if (!access || !refresh) {
      setError('Parametri di accesso mancanti')
      setLoading(false)
      return
    }

    setTokens(access, refresh)
    getMe()
      .then((user) => {
        setUser(user)
        navigate('/dashboard', { replace: true })
      })
      .catch(() => {
        setError('Sessione non valida')
      })
      .finally(() => setLoading(false))
  }, [searchParams, navigate, setUser])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <p className="text-slate-600">Accesso in corso...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-100 p-4">
        <p className="text-red-600">{error}</p>
        <Link to="/login" className="text-indigo-600 hover:underline">
          Torna al login
        </Link>
      </div>
    )
  }

  return null
}
