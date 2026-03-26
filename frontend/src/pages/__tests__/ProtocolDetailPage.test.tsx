import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProtocolDetailPage } from '../ProtocolDetailPage'

const { mockProtocol } = vi.hoisted(() => ({
  mockProtocol: {
    id: 'p1',
    protocol_id: '2026/TEST/1',
    subject: 'Oggetto test',
    direction: 'in',
    registered_at: '2026-01-01T00:00:00Z',
    document: null,
    attachments: [],
    dossiers: [],
  },
}))

vi.mock('../../services/protocolService', () => ({
  getProtocol: vi.fn().mockResolvedValue(mockProtocol),
  archiveProtocol: vi.fn(),
  downloadProtocolDocument: vi.fn(),
  addProtocolAttachment: vi.fn(),
}))

vi.mock('../../services/documentService', () => ({
  getDocuments: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../services/mailService', () => ({
  getMailMessages: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../components/viewer/DocumentViewer', () => ({
  DocumentViewer: () => null,
}))

vi.mock('../../components/signatures/SignaturePanel', () => ({
  SignaturePanel: () => null,
}))

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({ user: { id: 'u1', role: 'ADMIN' } }),
  ),
}))

vi.mock('../../components/layout/BreadcrumbContext', () => ({
  useBreadcrumbTitle: () => ({ setEntityTitle: vi.fn(), entityTitle: null }),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/protocols/p1']}>
      <Routes>
        <Route path="/protocols/:id" element={<ProtocolDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtocolDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading then protocol subject', async () => {
    renderPage()
    expect(screen.getByText(/Caricamento/i)).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText('Oggetto test')).toBeInTheDocument()
    })
  })

  it('shows documenti allegati tab', async () => {
    renderPage()
    expect(await screen.findByRole('button', { name: /Documenti allegati/i })).toBeInTheDocument()
  })
})
