import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { GlobalSearchBar } from '../GlobalSearchBar'

vi.mock('../../../services/searchService', () => ({
  search: vi.fn().mockResolvedValue({
    results: [
      {
        id: 'd1',
        title: 'Doc uno',
        description: '',
        status: 'APPROVED',
        current_version: 1,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-03-28T10:00:00Z',
        created_by_id: null,
        folder_id: null,
        folder_name: null,
        metadata_structure_id: null,
        snippet: null,
        score: null,
      },
    ],
  }),
}))

describe('GlobalSearchBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders global search input', () => {
    render(
      <MemoryRouter>
        <GlobalSearchBar />
      </MemoryRouter>,
    )
    expect(screen.getByLabelText(/Ricerca globale/i)).toBeInTheDocument()
  })

  it('shows dropdown results after debounced search', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <GlobalSearchBar />
      </MemoryRouter>,
    )
    await user.type(screen.getByLabelText(/Ricerca globale/i), 'doc')
    await waitFor(
      () => {
        expect(screen.getByText('Doc uno')).toBeInTheDocument()
      },
      { timeout: 3000 },
    )
  })
})
