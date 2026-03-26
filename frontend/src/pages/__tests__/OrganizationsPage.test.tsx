import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OrganizationsPage } from '../OrganizationsPage'
import { TestQueryProvider } from '../../test/queryWrapper'

vi.mock('../../services/organizationService', () => ({
  getOrganizationalUnitTree: vi.fn().mockResolvedValue([]),
  getOrganizationalUnits: vi.fn().mockResolvedValue({ results: [] }),
  createOrganizationalUnit: vi.fn(),
  updateOrganizationalUnit: vi.fn(),
  exportMembers: vi.fn(),
}))

vi.mock('../../services/userService', () => ({
  getUsers: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../services/groupService', () => ({
  getGroups: vi.fn().mockResolvedValue({ results: [] }),
  createGroup: vi.fn(),
  deleteGroup: vi.fn(),
}))

describe('OrganizationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows nuova U.O. button', () => {
    render(
      <MemoryRouter>
        <TestQueryProvider>
          <OrganizationsPage />
        </TestQueryProvider>
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: /Nuova U\.O\./i })).toBeInTheDocument()
  })

  it('renders unità organizzative heading', () => {
    render(
      <MemoryRouter>
        <TestQueryProvider>
          <OrganizationsPage />
        </TestQueryProvider>
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Unità Organizzative/i })).toBeInTheDocument()
  })
})
