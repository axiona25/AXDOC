import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { search } from '../../services/searchService'
import type { SearchResultItem } from '../../services/searchService'

const DEBOUNCE_MS = 300
const MAX_DROPDOWN = 5

export function GlobalSearchBar() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResultItem[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      setOpen(false)
      return
    }
    const t = setTimeout(() => {
      setLoading(true)
      search({ q: query, page_size: MAX_DROPDOWN })
        .then((res) => {
          setResults(res.results)
          setOpen(true)
        })
        .catch(() => setResults([]))
        .finally(() => setLoading(false))
    }, DEBOUNCE_MS)
    return () => clearTimeout(t)
  }, [query])

  useEffect(() => {
    const onOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('click', onOutside)
    return () => document.removeEventListener('click', onOutside)
  }, [])

  return (
    <div className="relative" ref={ref}>
      <input
        type="search"
        placeholder="Cerca documenti..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => query.trim() && results.length > 0 && setOpen(true)}
        className="w-64 rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 placeholder-slate-500"
        aria-label="Ricerca globale"
      />
      {loading && (
        <span className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden>...</span>
      )}
      {open && results.length > 0 && (
        <div className="absolute left-0 top-full z-50 mt-1 max-h-80 w-80 overflow-auto rounded border border-slate-200 bg-white shadow-lg">
          <ul className="py-1">
            {results.map((r) => (
              <li key={r.id}>
                <Link
                  to={`/documents?open=${r.id}`}
                  onClick={() => setOpen(false)}
                  className="block px-3 py-2 text-sm text-slate-800 hover:bg-slate-50"
                >
                  <span className="font-medium">{r.title}</span>
                  {r.folder_name && (
                    <span className="ml-2 text-slate-500">— {r.folder_name}</span>
                  )}
                  <span className="ml-2 text-slate-400">
                    {new Date(r.updated_at).toLocaleDateString('it-IT')}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          <Link
            to={`/search?q=${encodeURIComponent(query)}`}
            onClick={() => setOpen(false)}
            className="block border-t border-slate-100 px-3 py-2 text-center text-sm text-indigo-600 hover:bg-slate-50"
          >
            Vedi tutti
          </Link>
        </div>
      )}
    </div>
  )
}
