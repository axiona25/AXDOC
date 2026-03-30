import { useState, useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { BookOpen, FileText, FolderOpen, Users } from 'lucide-react'
import { search } from '../services/searchService'
import type { SearchResultItem, SearchResponse, SearchScope } from '../services/searchService'

const TABS: { id: SearchScope; label: string }[] = [
  { id: 'all', label: 'Tutti' },
  { id: 'documents', label: 'Documenti' },
  { id: 'protocols', label: 'Protocolli' },
  { id: 'dossiers', label: 'Fascicoli' },
  { id: 'contacts', label: 'Contatti' },
]

function resultHref(r: SearchResultItem): string {
  if (r.url) return r.url
  if (r.type === 'document' || !r.type) return `/documents?doc=${r.id}`
  return '/search'
}

function TypeIcon({ t }: { t?: string }) {
  const c = 'h-5 w-5 shrink-0'
  if (t === 'protocol') return <BookOpen className={`${c} text-emerald-600 dark:text-emerald-400`} aria-hidden />
  if (t === 'dossier') return <FolderOpen className={`${c} text-amber-600 dark:text-amber-400`} aria-hidden />
  if (t === 'contact') return <Users className={`${c} text-violet-600 dark:text-violet-400`} aria-hidden />
  return <FileText className={`${c} text-blue-600 dark:text-blue-400`} aria-hidden />
}

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const qFromUrl = searchParams.get('q') || ''
  const typeFromUrl = (searchParams.get('type') as SearchScope) || 'all'

  const [params, setParams] = useState<{
    q: string
    type: SearchScope
    status: string
    order_by: string
    page: number
    page_size: number
  }>({
    q: qFromUrl,
    type: typeFromUrl,
    status: '',
    order_by: 'relevance',
    page: 1,
    page_size: 20,
  })

  const [data, setData] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setParams((p) => ({
      ...p,
      q: searchParams.get('q') || '',
      type: ((searchParams.get('type') as SearchScope) || 'all') as SearchScope,
      page: 1,
    }))
  }, [searchParams.get('q'), searchParams.get('type')])

  useEffect(() => {
    const t = params.type
    if (!params.q.trim() && t !== 'all' && t !== 'documents') {
      setData({ results: [], total_count: 0, facets: {} })
      return
    }
    setLoading(true)
    const p: Record<string, string | number> = {
      q: params.q,
      type: params.type,
      page: params.page,
      page_size: params.page_size,
    }
    if (params.type === 'documents') {
      if (params.status) p.status = params.status
      if (params.order_by) p.order_by = params.order_by
    }
    search(p as Parameters<typeof search>[0])
      .then(setData)
      .catch(() => setData({ results: [], total_count: 0, facets: {} }))
      .finally(() => setLoading(false))
  }, [params.q, params.type, params.status, params.order_by, params.page, params.page_size])

  const facetCount = (key: string): number | undefined => {
    const f = data?.facets?.[key]
    if (typeof f === 'number') return f
    return undefined
  }

  const statusFacet = data?.facets?.status
  const statusMap =
    statusFacet && typeof statusFacet === 'object' && !Array.isArray(statusFacet)
      ? (statusFacet as Record<string, number>)
      : null

  return (
    <div className="min-h-screen bg-slate-100 p-6 dark:bg-slate-900">
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-4 text-2xl font-semibold text-slate-800 dark:text-slate-100">Ricerca</h1>
        <div className="mb-4 flex flex-wrap gap-2 border-b border-slate-200 pb-2 dark:border-slate-700">
          {TABS.map((tab) => {
            const count =
              tab.id === 'all'
                ? undefined
                : facetCount(
                    tab.id === 'documents'
                      ? 'documents'
                      : tab.id === 'protocols'
                        ? 'protocols'
                        : tab.id === 'dossiers'
                          ? 'dossiers'
                          : 'contacts',
                  )
            const active = params.type === tab.id
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setParams((p) => ({ ...p, type: tab.id, page: 1 }))
                  const next = new URLSearchParams(searchParams)
                  next.set('type', tab.id)
                  if (params.q) next.set('q', params.q)
                  setSearchParams(next)
                }}
                className={`rounded-full px-3 py-1.5 text-sm font-medium ${
                  active
                    ? 'bg-indigo-600 text-white dark:bg-indigo-500'
                    : 'bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-600'
                }`}
              >
                {tab.label}
                {count != null && count > 0 && (
                  <span className="ml-1.5 rounded-full bg-white/20 px-1.5 text-xs">{count}</span>
                )}
              </button>
            )
          })}
        </div>
        <div className="mb-4 flex flex-wrap gap-3">
          <input
            type="search"
            placeholder="Cerca..."
            value={params.q}
            onChange={(e) => {
              const v = e.target.value
              setParams((p) => ({ ...p, q: v, page: 1 }))
              const next = new URLSearchParams(searchParams)
              if (v) next.set('q', v)
              else next.delete('q')
              next.set('type', params.type)
              setSearchParams(next)
            }}
            className="min-w-[240px] flex-1 rounded border border-slate-300 bg-white px-3 py-2 text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
          />
          {params.type === 'documents' && (
            <>
              <select
                value={params.order_by}
                onChange={(e) =>
                  setParams((p) => ({ ...p, order_by: e.target.value, page: 1 }))
                }
                className="rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
              >
                <option value="relevance">Pertinenza</option>
                <option value="title">Titolo</option>
                <option value="-updated_at">Data (recente)</option>
                <option value="updated_at">Data (meno recente)</option>
              </select>
              {statusMap && Object.keys(statusMap).length > 0 && (
                <select
                  value={params.status}
                  onChange={(e) => setParams((p) => ({ ...p, status: e.target.value, page: 1 }))}
                  className="rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
                >
                  <option value="">Tutti gli stati</option>
                  {Object.entries(statusMap).map(([status, count]) => (
                    <option key={status} value={status}>
                      {status} ({count})
                    </option>
                  ))}
                </select>
              )}
            </>
          )}
        </div>
        {loading && <p className="text-slate-500 dark:text-slate-400">Caricamento...</p>}
        {data && !loading && (
          <>
            <p className="mb-2 text-sm text-slate-600 dark:text-slate-300">{data.total_count} risultati</p>
            <ul className="space-y-3">
              {data.results.map((r) => (
                <SearchResultCard key={`${r.type || 'doc'}-${r.id}`} item={r} />
              ))}
            </ul>
            {data.total_count > params.page_size && (
              <div className="mt-4 flex gap-2">
                <button
                  type="button"
                  disabled={params.page <= 1}
                  onClick={() => setParams((p) => ({ ...p, page: p.page - 1 }))}
                  className="rounded bg-slate-200 px-3 py-1.5 text-sm disabled:opacity-50 dark:bg-slate-700 dark:text-slate-100"
                >
                  Precedente
                </button>
                <button
                  type="button"
                  disabled={params.page * params.page_size >= data.total_count}
                  onClick={() => setParams((p) => ({ ...p, page: p.page + 1 }))}
                  className="rounded bg-slate-200 px-3 py-1.5 text-sm disabled:opacity-50 dark:bg-slate-700 dark:text-slate-100"
                >
                  Successiva
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function SearchResultCard({ item }: { item: SearchResultItem }) {
  const href = resultHref(item)
  const snippet = item.snippet || ''
  const plain = snippet.replace(/<[^>]+>/g, '')
  return (
    <li className="rounded border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <Link to={href} className="flex gap-3">
        <TypeIcon t={item.type} />
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-indigo-600 dark:text-indigo-400">{item.title}</h3>
          {(item.subtitle || item.folder_name) && (
            <p className="text-sm text-slate-500 dark:text-slate-400">{item.subtitle || item.folder_name}</p>
          )}
          {plain && (
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{plain}</p>
          )}
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
            {item.status && (
              <span className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-700">{item.status}</span>
            )}
            {item.updated_at && (
              <span>{new Date(item.updated_at).toLocaleDateString('it-IT')}</span>
            )}
          </div>
        </div>
      </Link>
    </li>
  )
}
