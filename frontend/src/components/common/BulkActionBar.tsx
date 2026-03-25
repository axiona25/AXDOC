import { useState } from 'react'
import { ConfirmModal } from './ConfirmModal'

export interface BulkActionItem {
  label: string
  icon: React.ReactNode
  onClick: () => void
  variant?: 'default' | 'danger'
  requireConfirm?: boolean
  confirmMessage?: string
  confirmTitle?: string
}

interface BulkActionBarProps {
  count: number
  onDeselectAll: () => void
  actions: BulkActionItem[]
}

export function BulkActionBar({ count, onDeselectAll, actions }: BulkActionBarProps) {
  const [pending, setPending] = useState<BulkActionItem | null>(null)

  if (count < 1) return null

  const runAction = (a: BulkActionItem) => {
    if (a.requireConfirm) {
      setPending(a)
      return
    }
    a.onClick()
  }

  const confirm = () => {
    if (pending) {
      pending.onClick()
      setPending(null)
    }
  }

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-indigo-100 bg-indigo-50 px-4 py-2.5 transition-all dark:border-indigo-900/50 dark:bg-indigo-950/40">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-indigo-900 dark:text-indigo-200">
            {count} {count === 1 ? 'elemento selezionato' : 'elementi selezionati'}
          </span>
          <button
            type="button"
            onClick={onDeselectAll}
            className="text-sm font-medium text-indigo-700 underline hover:text-indigo-900 dark:text-indigo-300 dark:hover:text-indigo-100"
          >
            Deseleziona tutto
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {actions.map((a) => (
            <button
              key={a.label}
              type="button"
              onClick={() => runAction(a)}
              className={`inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-sm font-medium ${
                a.variant === 'danger'
                  ? 'bg-red-600 text-white hover:bg-red-700 dark:hover:bg-red-500'
                  : 'bg-white text-indigo-800 shadow-sm ring-1 ring-indigo-200 hover:bg-indigo-100 dark:bg-slate-800 dark:text-indigo-200 dark:ring-indigo-800 dark:hover:bg-slate-700'
              }`}
            >
              {a.icon}
              {a.label}
            </button>
          ))}
        </div>
      </div>
      <ConfirmModal
        open={!!pending}
        title={pending?.confirmTitle ?? 'Conferma'}
        message={pending?.confirmMessage ?? 'Procedere?'}
        variant={pending?.variant === 'danger' ? 'danger' : 'primary'}
        confirmLabel="Conferma"
        onConfirm={confirm}
        onCancel={() => setPending(null)}
      />
    </>
  )
}
