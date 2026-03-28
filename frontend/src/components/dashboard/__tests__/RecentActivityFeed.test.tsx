import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { RecentActivityFeed } from '../RecentActivityFeed'

describe('RecentActivityFeed', () => {
  it('renders title', () => {
    render(
      <MemoryRouter>
        <RecentActivityFeed items={[]} />
      </MemoryRouter>,
    )
    expect(screen.getByText(/Attività recente/i)).toBeInTheDocument()
  })
})
