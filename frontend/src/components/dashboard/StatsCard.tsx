import type { ReactNode } from 'react'

type Variant = 'blue' | 'green' | 'orange' | 'red' | 'gray'

const variantClasses: Record<Variant, string> = {
  blue: 'bg-indigo-50 text-indigo-800 border-indigo-200 dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-200',
  green:
    'bg-emerald-50 text-emerald-800 border-emerald-200 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200',
  orange:
    'bg-amber-50 text-amber-800 border-amber-200 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200',
  red: 'bg-red-50 text-red-800 border-red-200 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200',
  gray: 'bg-slate-50 text-slate-800 border-slate-200 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100',
}

interface StatsCardProps {
  title: string
  value: number | string
  subtitle?: string
  icon?: ReactNode
  variant?: Variant
  /** Trend vs mese precedente (freccia + etichetta). */
  trend?: 'up' | 'down' | 'flat'
  trendLabel?: string
}

export function StatsCard({
  title,
  value,
  subtitle,
  icon,
  variant = 'blue',
  trend,
  trendLabel,
}: StatsCardProps) {
  return (
    <div className={`rounded-xl border p-4 ${variantClasses[variant]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium opacity-90">{title}</p>
          <p className="mt-1 text-2xl font-bold">{value}</p>
          {subtitle != null && <p className="mt-0.5 text-xs opacity-80">{subtitle}</p>}
          {trend && trendLabel != null && (
            <p
              className={`mt-1 flex items-center gap-1 text-xs font-medium ${
                trend === 'up'
                  ? 'text-emerald-700 dark:text-emerald-400'
                  : trend === 'down'
                    ? 'text-red-700 dark:text-red-400'
                    : 'text-slate-600 dark:text-slate-400'
              }`}
            >
              <span aria-hidden>{trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}</span>
              {trendLabel}
            </p>
          )}
        </div>
        {icon && <div className="text-2xl opacity-70">{icon}</div>}
      </div>
    </div>
  )
}
