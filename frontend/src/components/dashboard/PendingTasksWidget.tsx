import { Link } from 'react-router-dom'
import type { MyTaskItem } from '../../services/dashboardService'

interface PendingTasksWidgetProps {
  tasks: MyTaskItem[]
}

function isUrgent(deadline: string | null): boolean {
  if (!deadline) return false
  const d = new Date(deadline)
  const now = new Date()
  const days = (d.getTime() - now.getTime()) / 86400000
  return days >= 0 && days < 2
}

export function PendingTasksWidget({ tasks }: PendingTasksWidgetProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
      <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Step in attesa</h3>
      <ul className="mt-3 space-y-2">
        {tasks.length === 0 ? (
          <li className="text-sm text-slate-500 dark:text-slate-400">Nessun task in attesa</li>
        ) : (
          tasks.map((t) => (
            <li key={t.step_instance_id}>
              <Link
                to={`/documents?doc=${t.document_id}`}
                className="flex items-center justify-between rounded-lg border border-slate-100 p-2 text-sm hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-700/50"
              >
                <div>
                  <span className="font-medium text-slate-800 dark:text-slate-100">{t.document_title}</span>
                  <span className="ml-2 text-slate-600 dark:text-slate-300">— {t.step_name}</span>
                </div>
                {isUrgent(t.deadline) && (
                  <span className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-900/50 dark:text-amber-200">
                    Urgente
                  </span>
                )}
              </Link>
            </li>
          ))
        )}
      </ul>
    </div>
  )
}
