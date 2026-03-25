import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Filter } from 'lucide-react'

export interface FilterField {
  name: string
  label: string
  type: 'text' | 'select' | 'date' | 'date_range' | 'multiselect'
  options?: Array<{ value: string; label: string }>
  placeholder?: string
}

interface FilterPanelProps {
  fields: FilterField[]
  /** Parametri URL da leggere/scrivere (default: name dei fields) */
  urlKeys?: string[]
  onApply?: (filters: Record<string, string>) => void
  onReset?: () => void
}

function readFromParams(searchParams: URLSearchParams, keys: string[]): Record<string, string> {
  const out: Record<string, string> = {}
  for (const k of keys) {
    const v = searchParams.get(k)
    if (v != null && v !== '') out[k] = v
  }
  return out
}

export function FilterPanel({ fields, urlKeys, onApply, onReset }: FilterPanelProps) {
  const keys = useMemo(
    () => urlKeys ?? fields.map((f) => f.name),
    [fields, urlKeys],
  )
  const [searchParams, setSearchParams] = useSearchParams()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<Record<string, string>>(() => readFromParams(searchParams, keys))

  useEffect(() => {
    setDraft(readFromParams(searchParams, keys))
  }, [searchParams, keys.join('|')])

  const activeCount = useMemo(() => {
    let n = 0
    for (const k of keys) {
      const v = searchParams.get(k)
      if (v != null && v !== '') n += 1
    }
    return n
  }, [searchParams, keys])

  const setField = useCallback((name: string, value: string) => {
    setDraft((d) => ({ ...d, [name]: value }))
  }, [])

  const handleApply = () => {
    const next = new URLSearchParams(searchParams)
    for (const f of fields) {
      const v = draft[f.name]?.trim() ?? ''
      if (v) next.set(f.name, v)
      else next.delete(f.name)
    }
    setSearchParams(next, { replace: true })
    onApply?.(draft)
    setOpen(false)
  }

  const handleReset = () => {
    const next = new URLSearchParams(searchParams)
    for (const f of fields) {
      next.delete(f.name)
    }
    setSearchParams(next, { replace: true })
    setDraft({})
    onReset?.()
    setOpen(false)
  }

  return (
    <div className="mb-3 rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-600 dark:bg-slate-800">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700"
      >
        <span className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-indigo-600" aria-hidden />
          Filtri avanzati
          {activeCount > 0 && (
            <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-xs font-semibold text-white">{activeCount}</span>
          )}
        </span>
        <span className="text-slate-400 dark:text-slate-500">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="border-t border-slate-100 p-3 dark:border-slate-600">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {fields.map((f) => {
              if (f.type === 'date' || f.type === 'text') {
                return (
                  <label key={f.name} className="block">
                    <span className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">{f.label}</span>
                    <input
                      type={f.type === 'date' ? 'date' : 'text'}
                      value={draft[f.name] ?? ''}
                      onChange={(e) => setField(f.name, e.target.value)}
                      placeholder={f.placeholder}
                      className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
                    />
                  </label>
                )
              }
              if (f.type === 'select') {
                return (
                  <label key={f.name} className="block">
                    <span className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">{f.label}</span>
                    <select
                      value={draft[f.name] ?? ''}
                      onChange={(e) => setField(f.name, e.target.value)}
                      className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
                    >
                      <option value="">—</option>
                      {(f.options ?? []).map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </label>
                )
              }
              return null
            })}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleApply}
              className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 dark:hover:bg-indigo-500"
            >
              Applica
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="rounded border border-slate-300 px-4 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-500 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              Ripristina filtri
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
