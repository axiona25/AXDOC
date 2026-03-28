import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DocumentsTrendChart } from '../DocumentsTrendChart'

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: () => <div data-testid="bar-chart" />,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}))

describe('DocumentsTrendChart', () => {
  it('renders title', () => {
    render(<DocumentsTrendChart data={[]} />)
    expect(screen.getByText(/Documenti per mese/i)).toBeInTheDocument()
  })
})
