import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { LicensePage } from '../LicensePage'
import { TestQueryProvider } from '../../test/queryWrapper'

vi.mock('../../services/licenseService', () => ({
  getLicense: vi.fn().mockResolvedValue({
    license: null,
    stats: {
      active_users: 0,
      total_users: 0,
      storage_used_gb: 0,
      storage_limit_gb: null,
      documents_count: 0,
      expires_in_days: null,
      is_expired: false,
    },
  }),
  getSystemInfo: vi.fn().mockResolvedValue({ django_version: '4.2', python_version: '3.11' }),
}))

describe('LicensePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders licenza e sistema heading', async () => {
    render(
      <MemoryRouter>
        <TestQueryProvider>
          <LicensePage />
        </TestQueryProvider>
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Licenza e sistema/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText(/Caricamento/i)).not.toBeInTheDocument()
    })
  })

  it('shows dashboard link', () => {
    render(
      <MemoryRouter>
        <TestQueryProvider>
          <LicensePage />
        </TestQueryProvider>
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: /Dashboard/i })).toBeInTheDocument()
  })
})
