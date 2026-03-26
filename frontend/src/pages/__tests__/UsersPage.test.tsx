import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { UsersPage } from '../UsersPage'
import { TestQueryProvider } from '../../test/queryWrapper'

vi.mock('../../services/userService', () => ({
  getUsers: vi.fn().mockResolvedValue({ results: [], count: 0 }),
  getUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
}))

vi.mock('../../services/organizationService', () => ({
  getOrganizationalUnits: vi.fn().mockResolvedValue({ results: [] }),
}))

describe('UsersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows dashboard link in header', () => {
    render(
      <MemoryRouter>
        <TestQueryProvider>
          <UsersPage />
        </TestQueryProvider>
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: /Dashboard/i })).toBeInTheDocument()
  })

  it('renders gestione utenti', () => {
    render(
      <MemoryRouter>
        <TestQueryProvider>
          <UsersPage />
        </TestQueryProvider>
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Gestione Utenti/i })).toBeInTheDocument()
  })
})
