import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuditPage } from '../AuditPage'

vi.mock('../../services/auditService', () => ({
  getAuditLog: vi.fn().mockResolvedValue({ results: [], count: 0 }),
}))

vi.mock('../../services/exportService', () => ({
  exportAuditExcel: vi.fn(),
  exportAuditPdf: vi.fn(),
}))

vi.mock('../../components/common/ScreenReaderAnnouncer', () => ({
  announce: vi.fn(),
}))

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({ user: { id: '1', role: 'ADMIN' } }),
  ),
}))

describe('AuditPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows esporta excel button', async () => {
    render(
      <MemoryRouter initialEntries={['/audit']}>
        <AuditPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Esporta Excel/i })).toBeInTheDocument()
    })
  })

  it('renders registro attività for admin', async () => {
    render(
      <MemoryRouter initialEntries={['/audit']}>
        <AuditPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Registro attività/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText(/Caricamento/i)).not.toBeInTheDocument()
    })
  })
})
