import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DocumentsByStatusChart } from '../DocumentsByStatusChart'

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  PieChart: () => <div data-testid="pie-chart" />,
  Pie: () => null,
  Cell: () => null,
  Legend: () => null,
  Tooltip: () => null,
}))

describe('DocumentsByStatusChart', () => {
  it('renders section title', () => {
    render(<DocumentsByStatusChart documentsByStatus={{ DRAFT: 2, APPROVED: 1 }} />)
    expect(screen.getByText(/Documenti per stato/i)).toBeInTheDocument()
  })
})
