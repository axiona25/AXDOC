import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GenericViewer } from '../GenericViewer'

describe('GenericViewer', () => {
  it('shows default document label when fileName missing', () => {
    render(<GenericViewer />)
    expect(screen.getByText('Documento')).toBeInTheDocument()
  })

  it('shows file metadata and unavailable message', () => {
    render(<GenericViewer fileName="blob.bin" fileSize={2048} mimeType="application/octet-stream" />)
    expect(screen.getByText('blob.bin')).toBeInTheDocument()
    expect(screen.getByText(/Anteprima non disponibile/i)).toBeInTheDocument()
  })

  it('shows download button when onDownload provided', () => {
    render(<GenericViewer fileName="x" onDownload={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Scarica/i })).toBeInTheDocument()
  })
})
