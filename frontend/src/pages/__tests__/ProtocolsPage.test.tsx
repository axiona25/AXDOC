import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProtocolsPage } from '../ProtocolsPage'

vi.mock('../../services/protocolService', () => ({
  getProtocols: vi.fn().mockResolvedValue({ results: [], count: 0 }),
  archiveProtocol: vi.fn(),
  downloadProtocolDocument: vi.fn(),
}))

vi.mock('../../services/exportService', () => ({
  exportProtocolsExcel: vi.fn(),
  exportProtocolsPdf: vi.fn(),
}))

vi.mock('../../services/sharingService', () => ({
  shareProtocol: vi.fn(),
}))

vi.mock('../../services/signatureService', () => ({
  getSignaturesByTarget: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../services/organizationService', () => ({
  getOrganizationalUnits: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../components/protocols/ProtocolFormModal', () => ({
  ProtocolFormModal: () => null,
}))

vi.mock('../../components/sharing/ShareModal', () => ({
  ShareModal: () => null,
}))

describe('ProtocolsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows nuovo protocollo button', async () => {
    render(
      <MemoryRouter>
        <ProtocolsPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: /Nuovo protocollo/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText('Caricamento...')).not.toBeInTheDocument()
    })
  })

  it('renders protocollazione heading', async () => {
    render(
      <MemoryRouter>
        <ProtocolsPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Protocollazione/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText('Caricamento...')).not.toBeInTheDocument()
    })
  })
})
