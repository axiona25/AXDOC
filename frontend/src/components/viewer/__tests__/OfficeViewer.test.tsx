import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { OfficeViewer } from '../OfficeViewer'

vi.mock('react-pdf', () => ({
  Document: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  Page: () => null,
}))

describe('OfficeViewer', () => {
  it('shows conversion notice and embeds PdfViewer', () => {
    render(<OfficeViewer url="/c.pdf" originalFormat="DOCX" fileName="f.pdf" />)
    expect(screen.getByText(/Convertito da DOCX in PDF/i)).toBeInTheDocument()
    expect(screen.getByText(/Pagina 1/i)).toBeInTheDocument()
  })
})
