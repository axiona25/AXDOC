import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useChartTheme } from '../../hooks/useChartTheme'

interface DocumentsByStatusChartProps {
  documentsByStatus?: Record<string, number> | null
}

const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Bozza',
  IN_REVIEW: 'In revisione',
  APPROVED: 'Approvato',
  REJECTED: 'Rifiutato',
  ARCHIVED: 'Archiviato',
}

const STATUS_COLORS: Record<string, string> = {
  DRAFT: '#94a3b8',
  IN_REVIEW: '#f59e0b',
  APPROVED: '#22c55e',
  REJECTED: '#ef4444',
  ARCHIVED: '#1e3a5f',
}

export function DocumentsByStatusChart({ documentsByStatus }: DocumentsByStatusChartProps) {
  const { tooltipBg, tooltipBorder, axisColor, pieCellStroke } = useChartTheme()
  const data =
    documentsByStatus != null
      ? Object.entries(documentsByStatus)
          .map(([status, count]) => ({
            status,
            count,
            name: STATUS_LABELS[status] || status,
            fill: STATUS_COLORS[status] || '#94a3b8',
          }))
          .filter((d) => d.count > 0)
          .sort((a, b) => b.count - a.count)
      : []

  const total = data.reduce((s, d) => s + d.count, 0)

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Documenti per stato</h3>
      {data.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">Nessun dato</p>
      ) : (
        <div className="mt-2 flex flex-col gap-2 lg:flex-row lg:items-center">
          <div className="h-[260px] min-w-0 flex-1 no-transition">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={56}
                  outerRadius={88}
                  paddingAngle={2}
                  label={({ percent }) => `${((percent ?? 0) * 100).toFixed(0)}%`}
                >
                  {data.map((entry) => (
                    <Cell key={entry.status} fill={entry.fill} stroke={pieCellStroke} strokeWidth={1} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number, _n, item) => {
                    const p = item?.payload as { name?: string } | undefined
                    return [value, p?.name ?? '']
                  }}
                  contentStyle={{
                    borderRadius: 8,
                    border: `1px solid ${tooltipBorder}`,
                    backgroundColor: tooltipBg,
                    color: axisColor,
                  }}
                />
                <Legend
                  layout="vertical"
                  align="right"
                  verticalAlign="middle"
                  formatter={(value) => (
                    <span className="text-xs text-slate-700 dark:text-slate-200">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 lg:w-28">Totale: {total}</div>
        </div>
      )}
    </div>
  )
}
