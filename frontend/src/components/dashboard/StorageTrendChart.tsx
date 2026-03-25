import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { StorageTrendPoint } from '../../services/dashboardService'
import { useChartTheme } from '../../hooks/useChartTheme'

function monthLabel(ym: string): string {
  const [y, m] = ym.split('-').map(Number)
  if (!y || !m) return ym
  return new Date(y, m - 1, 1).toLocaleDateString('it-IT', { month: 'short' })
}

interface StorageTrendChartProps {
  data: StorageTrendPoint[]
}

export function StorageTrendChart({ data }: StorageTrendChartProps) {
  const chartData = data.map((d) => ({ ...d, label: monthLabel(d.month) }))
  const { axisColor, tooltipBg, tooltipBorder, gridColor } = useChartTheme()

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
        Storage — nuove versioni (MB / mese)
      </h3>
      {chartData.length === 0 ? (
        <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">Nessun dato</p>
      ) : (
        <div className="mt-4 h-[220px] w-full no-transition">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="label" tick={{ fontSize: 12, fill: axisColor }} stroke={axisColor} />
              <YAxis tick={{ fontSize: 12, fill: axisColor }} stroke={axisColor} />
              <Tooltip
                formatter={(v: number) => [`${v} MB`, 'Volume']}
                contentStyle={{
                  borderRadius: 8,
                  border: `1px solid ${tooltipBorder}`,
                  backgroundColor: tooltipBg,
                  color: axisColor,
                }}
              />
              <Line type="monotone" dataKey="mb" stroke="#0ea5e9" strokeWidth={2} dot name="MB" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
