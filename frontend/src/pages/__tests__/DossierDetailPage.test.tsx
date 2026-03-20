import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { DossierDetailPage } from '../DossierDetailPage'

const mockDossier = {
  id: 'dossier-1',
  title: 'Fascicolo test',
  identifier: '2026/CM/0001',
  status: 'open',
  responsible: 'user-1',
  responsible_email: 'resp@test.com',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  document_count: 0,
  protocol_count: 0,
  description: '',
  created_by: null,
  archived_at: null,
  documents: [],
  protocols: [],
  dossier_folders: [],
  dossier_emails: [],
  dossier_files: [],
  allowed_user_ids: [],
  allowed_ou_ids: [],
}

vi.mock('../../services/dossierService', () => ({
  getDossierDetail: vi.fn(() => Promise.resolve(mockDossier)),
  archiveDossier: vi.fn(),
  addDossierDocument: vi.fn(),
  removeDossierDocument: vi.fn(),
  addDossierProtocol: vi.fn(),
  removeDossierProtocol: vi.fn(),
  addDossierFolder: vi.fn(),
  removeDossierFolder: vi.fn(),
  addDossierEmail: vi.fn(),
  uploadDossierFile: vi.fn(),
  closeDossier: vi.fn(),
  generateDossierIndex: vi.fn(),
}))

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn(() => ({ user: { id: 'user-1', role: 'ADMIN' } })),
}))

function renderWithRouter() {
  return render(
    <MemoryRouter initialEntries={['/dossiers/dossier-1']}>
      <Routes>
        <Route path="/dossiers/:id" element={<DossierDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('DossierDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders dossier detail page', async () => {
    renderWithRouter()
    expect(await screen.findByText('Fascicolo test')).toBeInTheDocument()
    expect(await screen.findByText('2026/CM/0001')).toBeInTheDocument()
  })

  it('shows tab Documenti', async () => {
    renderWithRouter()
    await screen.findByText('Fascicolo test')
    const tab = screen.getByRole('button', { name: 'Documenti' })
    expect(tab).toBeInTheDocument()
  })

  it('shows tab Protocolli', async () => {
    renderWithRouter()
    await screen.findByText('Fascicolo test')
    const tab = screen.getByRole('button', { name: 'Protocolli' })
    expect(tab).toBeInTheDocument()
  })
})
