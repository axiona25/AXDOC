import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProtocolsTrendChart } from '../ProtocolsTrendChart'

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: () => <div data-testid="line-chart" />,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
}))

describe('ProtocolsTrendChart', () => {
  it('renders title', () => {
    render(<ProtocolsTrendChart data={[]} />)
    expect(screen.getByText(/Protocolli per mese/i)).toBeInTheDocument()
  })
})
