import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { FileExplorer } from '../FileExplorer'

vi.mock('../../../services/documentService', () => ({
  getFolders: vi.fn().mockResolvedValue([]),
  getDocuments: vi.fn().mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
}))
vi.mock('../../../services/metadataService', () => ({
  getMetadataStructures: vi.fn().mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
}))
vi.mock('../../viewer/DocumentViewer', () => ({ DocumentViewer: () => null }))

describe('FileExplorer', () => {
  it('renders and shows upload and new folder buttons', () => {
    render(
      <BrowserRouter>
        <FileExplorer />
      </BrowserRouter>
    )
    expect(screen.getByText(/Carica documento/i)).toBeDefined()
    expect(screen.getByText(/Nuova cartella/i)).toBeDefined()
  })
})
