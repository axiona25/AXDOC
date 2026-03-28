import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PackageWizard } from '../PackageWizard'

vi.mock('../../../services/archiveService', () => ({
  createPdv: vi.fn(),
}))

describe('PackageWizard', () => {
  it('returns null when closed', () => {
    const { container } = render(<PackageWizard open={false} onClose={vi.fn()} onSuccess={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('shows wizard title and steps when open', () => {
    render(<PackageWizard open onClose={vi.fn()} onSuccess={vi.fn()} />)
    expect(screen.getByRole('heading', { name: /Nuovo pacchetto PdV/i })).toBeInTheDocument()
    expect(screen.getByText(/1\. Documenti/i)).toBeInTheDocument()
  })
})
