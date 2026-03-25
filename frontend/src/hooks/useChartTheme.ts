import { useThemeStore } from '../store/themeStore'

export function useChartTheme() {
  const effectiveTheme = useThemeStore((s) => s.effectiveTheme)
  const isDark = effectiveTheme === 'dark'
  return {
    isDark,
    axisColor: isDark ? '#94a3b8' : '#64748b',
    tooltipBg: isDark ? '#1e293b' : '#ffffff',
    tooltipBorder: isDark ? '#475569' : '#e2e8f0',
    gridColor: isDark ? '#334155' : '#e2e8f0',
    legendColor: isDark ? '#e2e8f0' : '#334155',
    pieCellStroke: isDark ? '#1e293b' : '#ffffff',
  }
}
