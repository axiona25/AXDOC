import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { GroupsPage } from '../GroupsPage'
import { TestQueryProvider } from '../../test/queryWrapper'

vi.mock('../../services/groupService', () => ({
  getGroups: vi.fn().mockResolvedValue({ results: [] }),
  createGroup: vi.fn(),
  deleteGroup: vi.fn(),
}))

vi.mock('../../services/organizationService', () => ({
  getOrganizationalUnits: vi.fn().mockResolvedValue({ results: [] }),
}))

describe('GroupsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows search input for groups', () => {
    render(
      <MemoryRouter>
        <TestQueryProvider>
          <GroupsPage />
        </TestQueryProvider>
      </MemoryRouter>,
    )
    expect(screen.getByPlaceholderText(/Cerca per nome/i)).toBeInTheDocument()
  })

  it('renders gruppi heading', () => {
    render(
      <MemoryRouter>
        <TestQueryProvider>
          <GroupsPage />
        </TestQueryProvider>
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Gruppi utenti/i })).toBeInTheDocument()
  })
})
