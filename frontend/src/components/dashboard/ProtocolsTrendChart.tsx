import { useMemo } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ProtocolTrendPoint } from '../../services/dashboardService'
import { useChartTheme } from '../../hooks/useChartTheme'

function monthLabel(ym: string): string {
  const [y, m] = ym.split('-').map(Number)
  if (!y || !m) return ym
  return new Date(y, m - 1, 1).toLocaleDateString('it-IT', { month: 'short' })
}

function pivot(results: ProtocolTrendPoint[]) {
  const byMonth: Record<string, { month: string; label: string; in: number; out: number }> = {}
  for (const r of results) {
    if (!byMonth[r.month]) {
      byMonth[r.month] = { month: r.month, label: monthLabel(r.month), in: 0, out: 0 }
    }
    const d = r.direction?.toUpperCase()
    if (d === 'IN') byMonth[r.month].in += r.count
    else if (d === 'OUT') byMonth[r.month].out += r.count
  }
  return Object.values(byMonth).sort((a, b) => a.month.localeCompare(b.month))
}

interface ProtocolsTrendChartProps {
  data: ProtocolTrendPoint[]
}

export function ProtocolsTrendChart({ data }: ProtocolsTrendChartProps) {
  const chartData = useMemo(() => pivot(data), [data])
  const { axisColor, tooltipBg, tooltipBorder, gridColor, legendColor } = useChartTheme()

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Protocolli per mese (IN / OUT)</h3>
      {chartData.length === 0 ? (
        <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">Nessun dato nel periodo</p>
      ) : (
        <div className="mt-4 h-[300px] w-full no-transition">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="label" tick={{ fontSize: 12, fill: axisColor }} stroke={axisColor} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: axisColor }} stroke={axisColor} />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: `1px solid ${tooltipBorder}`,
                  backgroundColor: tooltipBg,
                  color: axisColor,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: legendColor }} />
              <Line type="monotone" dataKey="in" name="In entrata" stroke="#22c55e" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="out" name="In uscita" stroke="#3b82f6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
