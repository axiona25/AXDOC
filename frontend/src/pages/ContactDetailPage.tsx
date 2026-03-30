import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getContact } from '../services/contactService'

export function ContactDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [title, setTitle] = useState('')
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    getContact(id)
      .then((c) => {
        const name = [c.first_name, c.last_name].filter(Boolean).join(' ').trim()
        setTitle(name || c.company_name || c.email || id)
      })
      .catch(() => setErr('Contatto non trovato'))
  }, [id])

  return (
    <div className="min-h-screen bg-slate-100 p-6 dark:bg-slate-900">
      <div className="mx-auto max-w-lg rounded-lg border border-slate-200 bg-white p-6 shadow dark:border-slate-700 dark:bg-slate-800">
        <Link
          to="/search"
          className="mb-4 inline-block text-sm text-indigo-600 hover:underline dark:text-indigo-400"
        >
          ← Ricerca
        </Link>
        {err ? (
          <p className="text-red-600 dark:text-red-400">{err}</p>
        ) : (
          <h1 className="text-xl font-semibold text-slate-800 dark:text-slate-100">{title || '…'}</h1>
        )}
      </div>
    </div>
  )
}
