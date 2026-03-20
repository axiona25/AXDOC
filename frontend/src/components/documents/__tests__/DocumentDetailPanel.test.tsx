import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DocumentDetailPanel } from '../DocumentDetailPanel'
import type { DocumentItem } from '../../../services/documentService'

const mockDoc: DocumentItem = {
  id: 'doc-1',
  title: 'Test Doc',
  description: 'Desc',
  folder_id: null,
  status: 'APPROVED',
  current_version: 2,
  created_by: null,
  created_by_email: 'user@test.com',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  locked_by: null,
  locked_at: null,
  versions: [],
  attachments: [],
}

describe('DocumentDetailPanel', () => {
  it('returns null when document is null', () => {
    const { container } = render(
      <DocumentDetailPanel
        document={null}
        onClose={() => {}}
        onRefresh={() => {}}
        onNewVersion={() => {}}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders document title and tabs when document provided', () => {
    render(
      <DocumentDetailPanel
        document={mockDoc}
        onClose={() => {}}
        onRefresh={() => {}}
        onNewVersion={() => {}}
      />
    )
    expect(screen.getByText('Test Doc')).toBeDefined()
    expect(screen.getByText('Info')).toBeDefined()
    expect(screen.getByText('Versioni')).toBeDefined()
    expect(screen.getByText('Allegati')).toBeDefined()
    expect(screen.getByText('Scarica')).toBeDefined()
  })
})
