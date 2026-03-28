import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PdfViewer } from '../PdfViewer'

vi.mock('react-pdf', () => ({
  Document: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="pdf-document">{children}</div>
  ),
  Page: () => <div data-testid="pdf-page" />,
}))

describe('PdfViewer', () => {
  it('renders toolbar with page label and download when provided', () => {
    const onDownload = vi.fn()
    render(<PdfViewer url="/x.pdf" fileName="a.pdf" onDownload={onDownload} />)
    expect(screen.getByText(/Pagina 1/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Scarica/i })).toBeInTheDocument()
  })
})
