import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatsCard } from '../StatsCard'

describe('StatsCard', () => {
  it('renders title and value', () => {
    render(<StatsCard title="Documenti" value={42} variant="blue" />)
    expect(screen.getByText('Documenti')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('renders subtitle', () => {
    render(<StatsCard title="A" value="1" subtitle="dettaglio" />)
    expect(screen.getByText('dettaglio')).toBeInTheDocument()
  })
})
