import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { GroupDetailPage } from '../GroupDetailPage'
import { BreadcrumbProvider } from '../../components/layout/BreadcrumbContext'

const mockGetGroup = vi.fn()

vi.mock('../../services/groupService', () => ({
  getGroup: (...args: unknown[]) => mockGetGroup(...args),
}))

describe('GroupDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetGroup.mockResolvedValue({
      id: 'g1',
      name: 'Team Alpha',
      description: 'Desc',
      organizational_unit_name: 'UO1',
      members: [{ id: 'm1', user_name: 'Mario', user_email: 'm@test.com' }],
    })
  })

  it('shows error when getGroup fails', async () => {
    mockGetGroup.mockRejectedValueOnce(new Error('x'))
    render(
      <MemoryRouter initialEntries={['/groups/g1']}>
        <Routes>
          <Route
            path="/groups/:id"
            element={
              <BreadcrumbProvider>
                <GroupDetailPage />
              </BreadcrumbProvider>
            }
          />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(/Impossibile caricare il gruppo/i)).toBeInTheDocument()
    })
  })

  it('loads and shows group name and members', async () => {
    render(
      <MemoryRouter initialEntries={['/groups/g1']}>
        <Routes>
          <Route
            path="/groups/:id"
            element={
              <BreadcrumbProvider>
                <GroupDetailPage />
              </BreadcrumbProvider>
            }
          />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Team Alpha' })).toBeInTheDocument()
    })
    expect(screen.getByText(/U\.O\.: UO1/)).toBeInTheDocument()
    expect(screen.getByText(/m@test\.com/)).toBeInTheDocument()
  })
})
