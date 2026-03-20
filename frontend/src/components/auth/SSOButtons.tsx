import { useState, useEffect } from 'react'
import { api } from '../../services/api'

export function SSOButtons() {
  const [googleUrl, setGoogleUrl] = useState<string | null>(null)
  const [microsoftUrl, setMicrosoftUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get<{ auth_url: string }>('/api/auth/sso/google/').then((r) => r.data.auth_url).catch(() => null),
      api.get<{ auth_url: string }>('/api/auth/sso/microsoft/').then((r) => r.data.auth_url).catch(() => null),
    ]).then(([g, m]) => {
      setGoogleUrl(g ?? null)
      setMicrosoftUrl(m ?? null)
      setLoading(false)
    })
  }, [])

  if (loading || (!googleUrl && !microsoftUrl)) return null

  return (
    <div className="mt-6 space-y-2">
      <p className="text-center text-sm text-slate-500">oppure</p>
      <div className="flex flex-col gap-2">
        {googleUrl && (
          <a
            href={googleUrl}
            className="flex items-center justify-center gap-2 rounded border border-slate-300 bg-white py-2 px-4 text-slate-700 hover:bg-slate-50"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Accedi con Google
          </a>
        )}
        {microsoftUrl && (
          <a
            href={microsoftUrl}
            className="flex items-center justify-center gap-2 rounded border border-slate-300 bg-white py-2 px-4 text-slate-700 hover:bg-slate-50"
          >
            <svg className="h-5 w-5" viewBox="0 0 23 23">
              <path fill="#f35325" d="M1 1h10v10H1z" />
              <path fill="#81bc06" d="M12 1h10v10H12z" />
              <path fill="#05a6f0" d="M1 12h10v10H1z" />
              <path fill="#ffba08" d="M12 12h10v10H12z" />
            </svg>
            Accedi con Microsoft
          </a>
        )}
      </div>
    </div>
  )
}
