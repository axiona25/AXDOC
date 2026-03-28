import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PendingTasksWidget } from '../PendingTasksWidget'

describe('PendingTasksWidget', () => {
  it('renders empty message', () => {
    render(<PendingTasksWidget tasks={[]} />)
    expect(screen.getByText(/Step in attesa/i)).toBeInTheDocument()
  })
})
