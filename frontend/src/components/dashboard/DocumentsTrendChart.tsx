import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { MonthlyDataPoint } from '../../services/dashboardService'
import { useChartTheme } from '../../hooks/useChartTheme'

function monthLabel(ym: string): string {
  const [y, m] = ym.split('-').map(Number)
  if (!y || !m) return ym
  return new Date(y, m - 1, 1).toLocaleDateString('it-IT', { month: 'short' })
}

function monthFull(ym: string): string {
  const [y, m] = ym.split('-').map(Number)
  if (!y || !m) return ym
  return new Date(y, m - 1, 1).toLocaleDateString('it-IT', { month: 'long', year: 'numeric' })
}

interface DocumentsTrendChartProps {
  data: MonthlyDataPoint[]
}

export function DocumentsTrendChart({ data }: DocumentsTrendChartProps) {
  const { axisColor, tooltipBg, tooltipBorder, gridColor } = useChartTheme()
  const chartData = data.map((d) => ({
    ...d,
    label: monthLabel(d.month),
    monthFull: monthFull(d.month),
  }))

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Documenti per mese</h3>
      {chartData.length === 0 ? (
        <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">Nessun dato nel periodo</p>
      ) : (
        <div className="mt-4 h-[300px] w-full no-transition">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="label" tick={{ fontSize: 12, fill: axisColor }} stroke={axisColor} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: axisColor }} stroke={axisColor} />
              <Tooltip
                formatter={(value: number) => [value, 'Documenti']}
                labelFormatter={(_, payload) => {
                  const p = payload?.[0]?.payload as { monthFull?: string } | undefined
                  return p?.monthFull ?? ''
                }}
                contentStyle={{
                  borderRadius: 8,
                  border: `1px solid ${tooltipBorder}`,
                  backgroundColor: tooltipBg,
                  color: axisColor,
                }}
              />
              <Bar dataKey="count" fill="#6366f1" name="Documenti" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
