import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MyFilesPage } from '../MyFilesPage'

vi.mock('../../services/documentService', () => ({
  getMyFilesTree: vi.fn().mockResolvedValue({
    personal: { folders: [], documents: [] },
    office: { folders: [], documents: [] },
  }),
  getMyFiles: vi.fn().mockResolvedValue({ results: [] }),
  createFolder: vi.fn(),
  downloadDocument: vi.fn(),
  deleteDocument: vi.fn(),
  updateDocumentVisibility: vi.fn(),
  uploadDocument: vi.fn(),
}))

vi.mock('../../services/metadataService', () => ({
  getMetadataStructures: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../components/documents/UploadModal', () => ({
  UploadModal: () => null,
}))

vi.mock('../../components/viewer/DocumentViewer', () => ({
  DocumentViewer: () => null,
}))

describe('MyFilesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows personali tab', async () => {
    render(
      <MemoryRouter>
        <MyFilesPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Personali$/i })).toBeInTheDocument()
    })
  })

  it('renders i miei file heading', async () => {
    render(
      <MemoryRouter>
        <MyFilesPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /I miei File/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText(/Caricamento/i)).not.toBeInTheDocument()
    })
  })
})
