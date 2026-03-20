import type { ReactNode } from 'react'

type Variant = 'blue' | 'green' | 'orange' | 'red' | 'gray'

const variantClasses: Record<Variant, string> = {
  blue: 'bg-indigo-50 text-indigo-800 border-indigo-200',
  green: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  orange: 'bg-amber-50 text-amber-800 border-amber-200',
  red: 'bg-red-50 text-red-800 border-red-200',
  gray: 'bg-slate-50 text-slate-800 border-slate-200',
}

interface StatsCardProps {
  title: string
  value: number | string
  subtitle?: string
  icon?: ReactNode
  variant?: Variant
}

export function StatsCard({ title, value, subtitle, icon, variant = 'blue' }: StatsCardProps) {
  return (
    <div className={`rounded-xl border p-4 ${variantClasses[variant]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium opacity-90">{title}</p>
          <p className="mt-1 text-2xl font-bold">{value}</p>
          {subtitle != null && <p className="mt-0.5 text-xs opacity-80">{subtitle}</p>}
        </div>
        {icon && <div className="text-2xl opacity-70">{icon}</div>}
      </div>
    </div>
  )
}
