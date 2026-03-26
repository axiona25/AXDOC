import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SecurityIncidentsPage } from '../SecurityIncidentsPage'

vi.mock('../../services/securityService', () => ({
  fetchSecurityIncidents: vi.fn().mockResolvedValue({ results: [], count: 0 }),
  createSecurityIncident: vi.fn(),
  updateSecurityIncident: vi.fn(),
}))

vi.mock('../../services/exportService', () => ({
  exportIncidentsExcel: vi.fn(),
  exportIncidentsPdf: vi.fn(),
}))

vi.mock('../../components/security/IncidentFormModal', () => ({
  IncidentFormModal: () => null,
}))

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({ user: { id: '1', role: 'ADMIN' } }),
  ),
}))

describe('SecurityIncidentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows esporta excel for admin', async () => {
    render(
      <MemoryRouter>
        <SecurityIncidentsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Esporta Excel/i })).toBeInTheDocument()
    })
  })

  it('renders incidenti di sicurezza', async () => {
    render(
      <MemoryRouter>
        <SecurityIncidentsPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Incidenti di sicurezza/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText(/Caricamento/i)).not.toBeInTheDocument()
    })
  })
})
