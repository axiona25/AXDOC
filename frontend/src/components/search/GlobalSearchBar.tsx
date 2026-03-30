import { useState, useEffect, useRef, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, FileText, FolderOpen, Loader2, Users } from 'lucide-react'
import { search } from '../../services/searchService'
import type { SearchResultItem } from '../../services/searchService'

const DEBOUNCE_MS = 300
const MAX_DROPDOWN = 5

const TYPE_LABEL: Record<string, string> = {
  document: 'Documento',
  protocol: 'Protocollo',
  dossier: 'Fascicolo',
  contact: 'Contatto',
}

const TYPE_BADGE: Record<string, string> = {
  document: 'bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-200',
  protocol: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200',
  dossier: 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100',
  contact: 'bg-violet-100 text-violet-800 dark:bg-violet-900/50 dark:text-violet-200',
}

function resultHref(r: SearchResultItem): string {
  if (r.url) return r.url
  if (r.type === 'document' || !r.type) return `/documents?doc=${r.id}`
  return '/search'
}

function TypeIcon({ t }: { t?: string }) {
  const c = 'h-4 w-4 shrink-0 opacity-80'
  if (t === 'protocol') return <BookOpen className={c} aria-hidden />
  if (t === 'dossier') return <FolderOpen className={c} aria-hidden />
  if (t === 'contact') return <Users className={c} aria-hidden />
  return <FileText className={c} aria-hidden />
}

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
      search({ q: query, type: 'all', page_size: MAX_DROPDOWN })
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

  const grouped = useMemo(() => {
    const m: Record<string, SearchResultItem[]> = {
      document: [],
      protocol: [],
      dossier: [],
      contact: [],
    }
    for (const r of results) {
      const key = r.type || 'document'
      if (!m[key]) m[key] = []
      m[key].push(r)
    }
    return m
  }, [results])

  const sectionOrder: { key: keyof typeof grouped; label: string }[] = [
    { key: 'document', label: 'Documenti' },
    { key: 'protocol', label: 'Protocolli' },
    { key: 'dossier', label: 'Fascicoli' },
    { key: 'contact', label: 'Contatti' },
  ]

  return (
    <div className="relative" ref={ref}>
      <input
        type="search"
        placeholder="Cerca in AXDOC..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => query.trim() && results.length > 0 && setOpen(true)}
        className="w-64 rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 placeholder-slate-500 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 dark:placeholder-slate-400"
        aria-label="Ricerca globale"
      />
      {loading && (
        <Loader2
          className="absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-slate-400"
          aria-hidden
        />
      )}
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 max-h-96 w-[min(100vw-2rem,22rem)] overflow-auto rounded border border-slate-200 bg-white shadow-lg dark:border-slate-600 dark:bg-slate-800">
          {results.length === 0 && query.trim() && !loading ? (
            <p className="px-3 py-4 text-sm text-slate-600 dark:text-slate-300">
              Nessun risultato per &quot;{query}&quot;
            </p>
          ) : (
            <div className="py-1">
              {sectionOrder.map(({ key, label }) => {
                const items = grouped[key] || []
                if (items.length === 0) return null
                return (
                  <div key={key} className="mb-2 last:mb-0">
                    <p className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      {label}
                    </p>
                    <ul>
                      {items.map((r) => (
                        <li key={`${key}-${r.id}`}>
                          <Link
                            to={resultHref(r)}
                            onClick={() => setOpen(false)}
                            className="flex gap-2 px-3 py-2 text-sm text-slate-800 hover:bg-slate-50 dark:text-slate-100 dark:hover:bg-slate-700"
                          >
                            <TypeIcon t={r.type} />
                            <span className="min-w-0 flex-1">
                              <span className="flex flex-wrap items-center gap-2">
                                <span className="font-medium">{r.title}</span>
                                <span
                                  className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${TYPE_BADGE[r.type || 'document']}`}
                                >
                                  {TYPE_LABEL[r.type || 'document']}
                                </span>
                              </span>
                              {(r.subtitle || r.folder_name) && (
                                <span className="block truncate text-xs text-slate-500 dark:text-slate-400">
                                  {r.subtitle || r.folder_name}
                                </span>
                              )}
                              {r.snippet && (
                                <span className="mt-0.5 line-clamp-2 block text-xs text-slate-600 dark:text-slate-300">
                                  {r.snippet.replace(/<[^>]+>/g, '')}
                                </span>
                              )}
                            </span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                )
              })}
            </div>
          )}
          {query.trim() && (
            <Link
              to={`/search?q=${encodeURIComponent(query)}`}
              onClick={() => setOpen(false)}
              className="block border-t border-slate-100 px-3 py-2 text-center text-sm text-indigo-600 hover:bg-slate-50 dark:border-slate-600 dark:text-indigo-400 dark:hover:bg-slate-700"
            >
              Ricerca avanzata
            </Link>
          )}
        </div>
      )}
    </div>
  )
}
