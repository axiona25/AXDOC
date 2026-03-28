import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WorkflowStatsWidget } from '../WorkflowStatsWidget'

describe('WorkflowStatsWidget', () => {
  it('renders loading when stats null', () => {
    render(<WorkflowStatsWidget stats={null} />)
    expect(screen.getByText(/Workflow/i)).toBeInTheDocument()
    expect(screen.getByText(/Caricamento/i)).toBeInTheDocument()
  })

  it('renders stats heading when data present', () => {
    render(
      <WorkflowStatsWidget
        stats={{
          active: 1,
          completed_total: 5,
          completed_this_month: 2,
          rejected: 0,
          cancelled: 0,
          avg_completion_hours: 1.5,
        }}
      />,
    )
    expect(screen.getByText(/Statistiche workflow/i)).toBeInTheDocument()
  })
})
