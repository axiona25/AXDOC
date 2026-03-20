import { useState, useEffect } from 'react'
import { getTitolario } from '../../services/archiveService'
import type { TitolarioNode } from '../../services/archiveService'

interface ClassificationSelectProps {
  value: string
  onChange: (code: string, label: string, retentionYears?: number) => void
  placeholder?: string
  className?: string
  disabled?: boolean
}

export function ClassificationSelect({
  value,
  onChange,
  placeholder = 'Seleziona classificazione',
  className = '',
  disabled = false,
}: ClassificationSelectProps) {
  const [tree, setTree] = useState<TitolarioNode[]>([])
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getTitolario()
      .then(setTree)
      .catch(() => setTree([]))
      .finally(() => setLoading(false))
  }, [])

  const flatOptions: { code: string; label: string; retention?: number; fullLabel: string }[] = []
  tree.forEach((node) => {
    node.children?.forEach((ch) => {
      flatOptions.push({
        code: ch.code,
        label: ch.label,
        retention: ch.retention ?? ch.rule?.retention_years,
        fullLabel: `${ch.code} - ${ch.label}`,
      })
    })
  })

  const filtered = search.trim()
    ? flatOptions.filter(
        (o) =>
          o.code.toLowerCase().includes(search.toLowerCase()) ||
          o.label.toLowerCase().includes(search.toLowerCase())
      )
    : flatOptions

  const selected = flatOptions.find((o) => o.code === value)

  return (
    <div className={`relative ${className}`}>
      <div className="flex gap-2">
        <input
          type="text"
          value={open ? search : (selected?.fullLabel ?? value ?? '')}
          onChange={(e) => (open ? setSearch(e.target.value) : setOpen(true))}
          onFocus={() => setOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          className="min-w-[200px] rounded border border-slate-300 px-2 py-1.5 text-sm"
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange('', '')}
            className="text-slate-500 hover:text-slate-700"
            title="Cancella"
          >
            ✕
          </button>
        )}
      </div>
      {open && (
        <div className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded border border-slate-200 bg-white shadow">
          {loading ? (
            <p className="p-2 text-sm text-slate-500">Caricamento...</p>
          ) : (
            filtered.slice(0, 50).map((opt) => (
              <button
                key={opt.code}
                type="button"
                className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-100"
                onClick={() => {
                  onChange(opt.code, opt.label, opt.retention)
                  setOpen(false)
                  setSearch('')
                }}
              >
                {opt.fullLabel}
                {opt.retention != null && <span className="ml-2 text-slate-400">({opt.retention} anni)</span>}
              </button>
            ))
          )}
        </div>
      )}
      {open && <div className="fixed inset-0 z-0" onClick={() => setOpen(false)} aria-hidden />}
    </div>
  )
}
