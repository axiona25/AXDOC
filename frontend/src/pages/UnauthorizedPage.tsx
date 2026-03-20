import { Link } from 'react-router-dom'

export function UnauthorizedPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-100 p-4">
      <h1 className="text-xl font-bold text-slate-800">Accesso non autorizzato</h1>
      <p className="mt-2 text-slate-600">Non hai i permessi per visualizzare questa pagina.</p>
      <Link
        to="/dashboard"
        className="mt-4 rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700"
      >
        Torna alla dashboard
      </Link>
    </div>
  )
}
