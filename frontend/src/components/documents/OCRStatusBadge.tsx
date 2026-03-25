import { Loader2 } from 'lucide-react'

export type OCRStatusValue =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'not_needed'
  | string
  | undefined

const STYLES: Record<string, string> = {
  pending: 'bg-slate-200 text-slate-700 dark:bg-slate-600 dark:text-slate-100',
  processing: 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200',
  completed: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-200',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200',
  not_needed: 'bg-sky-100 text-sky-900 dark:bg-sky-900/40 dark:text-sky-200',
}

interface OCRStatusBadgeProps {
  status: OCRStatusValue
  confidence?: number | null
  error?: string
  onRetry?: () => void
  retrying?: boolean
  compact?: boolean
}

export function OCRStatusBadge({
  status,
  confidence,
  error,
  onRetry,
  retrying,
  compact,
}: OCRStatusBadgeProps) {
  const s = status || 'pending'
  const label =
    s === 'pending'
      ? 'OCR in attesa'
      : s === 'processing'
        ? 'OCR in corso…'
        : s === 'completed'
          ? 'Testo estratto'
          : s === 'failed'
            ? 'OCR fallito'
            : s === 'not_needed'
              ? 'Testo nativo'
              : s

  const base = `inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[s] ?? STYLES.pending}`

  return (
    <span className={compact ? 'inline-flex flex-col items-start gap-1' : 'flex flex-col gap-1'}>
      <span className={base}>
        {s === 'processing' && <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" aria-hidden />}
        {label}
        {s === 'completed' && confidence != null && confidence > 0 && (
          <span className="opacity-80">({Math.round(confidence)}%)</span>
        )}
      </span>
      {s === 'failed' && error && !compact && (
        <span className="max-w-md text-xs text-red-600 dark:text-red-300" title={error}>
          {error.slice(0, 120)}
          {error.length > 120 ? '…' : ''}
        </span>
      )}
      {s === 'failed' && onRetry && (
        <button
          type="button"
          disabled={retrying}
          onClick={onRetry}
          className="text-xs font-medium text-indigo-600 hover:underline disabled:opacity-50 dark:text-indigo-400"
        >
          {retrying ? 'Avvio…' : 'Riprova OCR'}
        </button>
      )}
    </span>
  )
}
