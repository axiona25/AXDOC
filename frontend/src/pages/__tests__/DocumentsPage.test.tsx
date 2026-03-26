import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { DocumentsPage } from '../DocumentsPage'

vi.mock('../../components/documents/FileExplorer', () => ({
  FileExplorer: () => <div data-testid="file-explorer">Explorer</div>,
}))

describe('DocumentsPage', () => {
  it('shows link to P7M verify', () => {
    render(
      <MemoryRouter>
        <DocumentsPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: /Verifica P7M/i })).toBeInTheDocument()
  })

  it('renders title and file explorer', () => {
    render(
      <MemoryRouter>
        <DocumentsPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Documenti/i })).toBeInTheDocument()
    expect(screen.getByTestId('file-explorer')).toBeInTheDocument()
  })
})
