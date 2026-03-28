import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { RecentDocumentsWidget } from '../RecentDocumentsWidget'

describe('RecentDocumentsWidget', () => {
  it('renders title', () => {
    render(
      <MemoryRouter>
        <RecentDocumentsWidget documents={[]} />
      </MemoryRouter>,
    )
    expect(screen.getByText(/Documenti recenti/i)).toBeInTheDocument()
  })
})
