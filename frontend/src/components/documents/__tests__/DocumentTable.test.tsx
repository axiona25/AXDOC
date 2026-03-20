import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DocumentTable } from '../DocumentTable'
import type { DocumentItem } from '../../../services/documentService'

const mockDoc: DocumentItem = {
  id: 'doc-1',
  title: 'Test Document',
  description: '',
  folder_id: null,
  status: 'DRAFT',
  current_version: 1,
  created_by: null,
  created_by_email: 'user@test.com',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  locked_by: null,
  locked_at: null,
}

describe('DocumentTable', () => {
  it('renders document list with columns', () => {
    render(
      <DocumentTable
        documents={[mockDoc]}
        onOpen={() => {}}
        onDownload={() => {}}
      />
    )
    expect(screen.getByText('Test Document')).toBeDefined()
    expect(screen.getByText('v1')).toBeDefined()
    expect(screen.getByText('DRAFT')).toBeDefined()
  })

  it('shows empty state when no documents', () => {
    render(
      <DocumentTable
        documents={[]}
        onOpen={() => {}}
        onDownload={() => {}}
      />
    )
    expect(screen.getByText(/Nessun documento in questa cartella/i)).toBeDefined()
  })
})
