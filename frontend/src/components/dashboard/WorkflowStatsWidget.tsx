import { Archive, Ban, CheckCircle, Clock, Play, XCircle } from 'lucide-react'
import type { WorkflowStats } from '../../services/dashboardService'

function formatAvgHours(h: number | null): string {
  if (h == null) return '—'
  const totalMin = Math.round(h * 60)
  const hh = Math.floor(totalMin / 60)
  const mm = totalMin % 60
  return `${hh}h ${mm}m`
}

interface MiniKpiProps {
  label: string
  value: number | string
  icon: React.ReactNode
  className: string
}

function MiniKpi({ label, value, icon, className }: MiniKpiProps) {
  return (
    <div
      className={`flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50/80 p-3 dark:border-slate-600 dark:bg-slate-700/50 ${className}`}
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white shadow-sm dark:bg-slate-800">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
        <p className="truncate text-lg font-semibold text-slate-800 dark:text-slate-100">{value}</p>
      </div>
    </div>
  )
}

interface WorkflowStatsWidgetProps {
  stats: WorkflowStats | null
}

export function WorkflowStatsWidget({ stats }: WorkflowStatsWidgetProps) {
  if (!stats) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Workflow</h3>
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">Caricamento...</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Statistiche workflow</h3>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <MiniKpi
          label="Attivi"
          value={stats.active}
          icon={<Play className="h-4 w-4 text-blue-600" aria-hidden />}
          className=""
        />
        <MiniKpi
          label="Completati (mese)"
          value={stats.completed_this_month}
          icon={<CheckCircle className="h-4 w-4 text-emerald-600" aria-hidden />}
          className=""
        />
        <MiniKpi
          label="Rifiutati"
          value={stats.rejected}
          icon={<XCircle className="h-4 w-4 text-red-600" aria-hidden />}
          className=""
        />
        <MiniKpi
          label="Cancellati"
          value={stats.cancelled}
          icon={<Ban className="h-4 w-4 text-slate-500" aria-hidden />}
          className=""
        />
        <MiniKpi
          label="Completati totali"
          value={stats.completed_total}
          icon={<Archive className="h-4 w-4 text-indigo-600" aria-hidden />}
          className=""
        />
        <MiniKpi
          label="Tempo medio"
          value={formatAvgHours(stats.avg_completion_hours)}
          icon={<Clock className="h-4 w-4 text-amber-600" aria-hidden />}
          className=""
        />
      </div>
    </div>
  )
}
