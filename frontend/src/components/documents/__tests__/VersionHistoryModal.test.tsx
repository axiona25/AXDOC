import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { VersionHistoryModal } from '../VersionHistoryModal'

vi.mock('../../../services/documentService', () => ({
  downloadDocument: vi.fn(),
}))

describe('VersionHistoryModal', () => {
  it('renders title with document name', () => {
    render(
      <VersionHistoryModal
        open
        onClose={() => {}}
        documentId="d1"
        title="Doc A"
        versions={[]}
      />,
    )
    expect(screen.getByRole('heading', { name: /Storico versioni — Doc A/i })).toBeInTheDocument()
    expect(screen.getByText('Versione')).toBeInTheDocument()
  })

  it('shows version row', () => {
    render(
      <VersionHistoryModal
        open
        onClose={() => {}}
        documentId="d1"
        title="Doc"
        versions={[
          {
            id: 'v1',
            version_number: 2,
            file_name: 'a.pdf',
            created_at: '2025-01-01T12:00:00Z',
            change_description: 'note',
            is_current: true,
          } as never,
        ]}
      />,
    )
    expect(screen.getByText(/v2/)).toBeInTheDocument()
    expect(screen.getByText('a.pdf')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Scarica/i })).toBeInTheDocument()
  })
})
