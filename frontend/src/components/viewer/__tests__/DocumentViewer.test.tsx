import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ImageViewer } from '../ImageViewer'

vi.mock('../../../services/documentService', () => ({
  getViewerInfo: vi.fn(),
  getPreviewBlobUrl: vi.fn(),
  getPreviewJson: vi.fn(),
  downloadDocument: vi.fn(),
}))

vi.mock('../PdfViewer', () => ({ PdfViewer: () => <div data-testid="pdf-viewer">PDF</div> }))
vi.mock('../OfficeViewer', () => ({ OfficeViewer: () => <div>Office</div> }))

import { DocumentViewer } from '../DocumentViewer'

describe('DocumentViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders with viewer_type pdf', async () => {
    const { getViewerInfo, getPreviewBlobUrl } = await import('../../../services/documentService')
    vi.mocked(getViewerInfo).mockResolvedValue({
      viewer_type: 'pdf',
      mime_type: 'application/pdf',
      file_name: 'doc.pdf',
      file_size: 1024,
    })
    vi.mocked(getPreviewBlobUrl).mockResolvedValue({ url: 'blob:http://localhost/pdf', viewerType: 'pdf' })

    render(<DocumentViewer documentId="doc-1" showHeader />)
    await waitFor(() => {
      expect(screen.queryByText(/Caricamento/)).not.toBeInTheDocument()
    })
    expect(screen.getByText(/doc\.pdf/)).toBeInTheDocument()
  })

  it('renders with viewer_type generic', async () => {
    const { getViewerInfo } = await import('../../../services/documentService')
    vi.mocked(getViewerInfo).mockResolvedValue({
      viewer_type: 'generic',
      mime_type: 'application/octet-stream',
      file_name: 'file.bin',
      file_size: 512,
    })

    render(<DocumentViewer documentId="doc-2" showHeader />)
    await waitFor(() => {
      expect(screen.queryByText(/Caricamento/)).not.toBeInTheDocument()
    })
    expect(screen.getByText(/Anteprima non disponibile/)).toBeInTheDocument()
  })
})

describe('ImageViewer', () => {
  it('renders with url', () => {
    render(<ImageViewer url="blob:http://test/img" fileName="test.png" />)
    const img = document.querySelector('img')
    expect(img).toBeInTheDocument()
    expect(img?.getAttribute('src')).toBe('blob:http://test/img')
  })
})
