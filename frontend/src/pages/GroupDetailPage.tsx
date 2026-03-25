import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getGroup, type UserGroupMember } from '../services/groupService'
import { useBreadcrumbTitle } from '../components/layout/BreadcrumbContext'

export function GroupDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { setEntityTitle } = useBreadcrumbTitle()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [ouName, setOuName] = useState<string | null>(null)
  const [members, setMembers] = useState<UserGroupMember[]>([])

  useEffect(() => {
    if (!id) {
      setLoading(false)
      setError('Gruppo non trovato.')
      return
    }
    setLoading(true)
    setError(null)
    getGroup(id)
      .then((g) => {
        setName(g.name)
        setDescription(g.description || '')
        setOuName(g.organizational_unit_name ?? null)
        setMembers(g.members ?? [])
      })
      .catch(() => setError('Impossibile caricare il gruppo.'))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (name) setEntityTitle(name)
    else setEntityTitle(null)
    return () => setEntityTitle(null)
  }, [name, setEntityTitle])

  return (
    <div className="min-h-screen bg-slate-100 p-6">
      <div className="mx-auto max-w-2xl rounded-lg border border-slate-200 bg-white p-6 shadow">
        <Link to="/organizations" className="text-sm text-indigo-600 hover:underline">
          ← Organizzazioni
        </Link>
        {loading ? (
          <p className="mt-4 text-slate-600">Caricamento...</p>
        ) : error ? (
          <p className="mt-4 text-red-600">{error}</p>
        ) : (
          <>
            <h1 className="mt-4 text-xl font-bold text-slate-800">{name}</h1>
            {ouName && <p className="text-sm text-slate-500">U.O.: {ouName}</p>}
            {description && <p className="mt-2 text-sm text-slate-600">{description}</p>}
            <h2 className="mt-6 text-sm font-semibold text-slate-700">Membri</h2>
            <ul className="mt-2 space-y-2">
              {members.length === 0 && <li className="text-sm text-slate-500">Nessun membro.</li>}
              {members.map((m) => (
                <li key={m.id} className="rounded border border-slate-100 px-3 py-2 text-sm">
                  {m.user_name} ({m.user_email})
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  )
}
