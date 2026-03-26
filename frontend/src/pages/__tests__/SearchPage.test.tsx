import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SearchPage } from '../SearchPage'

vi.mock('../../services/searchService', () => ({
  search: vi.fn().mockResolvedValue({ results: [], total_count: 0, facets: {} }),
}))

describe('SearchPage', () => {
  it('shows order by pertinenza', () => {
    render(
      <MemoryRouter>
        <SearchPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('option', { name: /Pertinenza/i })).toBeInTheDocument()
  })

  it('renders ricerca heading and search input', () => {
    render(
      <MemoryRouter>
        <SearchPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Ricerca/i })).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Cerca documenti/i)).toBeInTheDocument()
  })
})
