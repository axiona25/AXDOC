import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StorageTrendChart } from '../StorageTrendChart'

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: () => <div data-testid="line-chart" />,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}))

describe('StorageTrendChart', () => {
  it('renders title', () => {
    render(<StorageTrendChart data={[]} />)
    expect(screen.getByText(/Storage/i)).toBeInTheDocument()
  })
})
