import { useState, useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { search } from '../services/searchService'
import type { SearchResultItem, SearchResponse } from '../services/searchService'

export function SearchPage() {
  const [searchParams] = useSearchParams()
  const q = searchParams.get('q') || ''
  const [params, setParams] = useState<{
    q: string
    type: 'documents'
    status: string
    order_by: string
    page: number
    page_size: number
  }>({
    q,
    type: 'documents',
    status: '',
    order_by: 'relevance',
    page: 1,
    page_size: 20,
  })
  const [data, setData] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setParams((p) => ({ ...p, q: searchParams.get('q') || '', page: 1 }))
  }, [searchParams.get('q')])

  useEffect(() => {
    if (!params.q.trim()) {
      setData({ results: [], total_count: 0, facets: {} })
      return
    }
    setLoading(true)
    const p: Record<string, string | number> = { ...params }
    if (!p.status) delete p.status
    search(p as Parameters<typeof search>[0])
      .then(setData)
      .catch(() => setData({ results: [], total_count: 0, facets: {} }))
      .finally(() => setLoading(false))
  }, [params.q, params.type, params.status, params.order_by, params.page])

  return (
    <div className="min-h-screen bg-slate-100 p-6 dark:bg-slate-900">
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-4 text-2xl font-semibold text-slate-800 dark:text-slate-100">Ricerca</h1>
        <div className="mb-4 flex flex-wrap gap-3">
          <input
            type="search"
            placeholder="Cerca documenti..."
            value={params.q}
            onChange={(e) => setParams((p) => ({ ...p, q: e.target.value, page: 1 }))}
            className="min-w-[240px] flex-1 rounded border border-slate-300 bg-white px-3 py-2 text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
          />
          <select
            value={params.order_by}
            onChange={(e) => setParams((p) => ({ ...p, order_by: e.target.value as 'relevance' | 'title' | '-updated_at' | 'updated_at' }))}
            className="rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
          >
            <option value="relevance">Pertinenza</option>
            <option value="title">Titolo</option>
            <option value="-updated_at">Data (recente)</option>
            <option value="updated_at">Data (meno recente)</option>
          </select>
          {data?.facets?.status && Object.keys(data.facets.status).length > 0 && (
            <select
              value={params.status}
              onChange={(e) => setParams((p) => ({ ...p, status: e.target.value, page: 1 }))}
              className="rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
            >
              <option value="">Tutti gli stati</option>
              {Object.entries(data.facets.status).map(([status, count]) => (
                <option key={status} value={status}>{status} ({count})</option>
              ))}
            </select>
          )}
        </div>
        {loading && <p className="text-slate-500 dark:text-slate-400">Caricamento...</p>}
        {data && !loading && (
          <>
            <p className="mb-2 text-sm text-slate-600 dark:text-slate-300">{data.total_count} risultati</p>
            <ul className="space-y-3">
              {data.results.map((r) => (
                <SearchResultCard key={r.id} item={r} />
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
  return (
    <li className="rounded border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <Link to={`/documents?open=${item.id}`} className="block">
        <h3 className="font-semibold text-indigo-600 dark:text-indigo-400">{item.title}</h3>
        {item.snippet && (
          <p
            className="mt-1 text-sm text-slate-600 dark:text-slate-300"
            dangerouslySetInnerHTML={{ __html: item.snippet }}
          />
        )}
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
          <span className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-700">{item.status}</span>
          {item.folder_name && <span>{item.folder_name}</span>}
          <span>{new Date(item.updated_at).toLocaleDateString('it-IT')}</span>
        </div>
      </Link>
      <div className="mt-2">
        <Link
          to={`/documents?open=${item.id}`}
          className="mr-2 text-sm text-indigo-600 hover:underline"
        >
          Apri
        </Link>
      </div>
    </li>
  )
}
