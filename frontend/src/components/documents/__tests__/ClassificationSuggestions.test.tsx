import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ClassificationSuggestions } from '../ClassificationSuggestions'

const doc = {
  id: 'd1',
  title: 'Doc',
  description: '',
  folder_id: 'f1',
  status: 'DRAFT',
  current_version: 1,
  created_by: null,
  created_by_email: null,
  created_at: '',
  updated_at: '',
  locked_by: null,
  locked_at: null,
} as import('../../../services/documentService').DocumentItem

vi.mock('../../../services/documentService', () => ({
  classifyDocument: vi.fn().mockResolvedValue({
    suggestions: [{ type: 'fattura', label: 'Fattura', confidence: 0.85, method: 'rule_based' }],
    metadata_suggestions: { amount: '100' },
    workflow_suggestion: null,
    classification_suggestion: null,
  }),
  updateDocument: vi.fn(),
  updateDocumentMetadata: vi.fn(),
  startDocumentWorkflow: vi.fn(),
}))

vi.mock('../../../services/metadataService', () => ({
  getMetadataStructure: vi.fn().mockResolvedValue(null),
}))

describe('ClassificationSuggestions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('runs analyze and shows suggestion and apply button', async () => {
    const user = userEvent.setup()
    const onRefresh = vi.fn()
    render(<ClassificationSuggestions document={doc} onRefresh={onRefresh} />)
    await user.click(screen.getByRole('button', { name: /Analizza documento/i }))
    await waitFor(() => {
      expect(screen.getByText('Fattura')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Applica suggerimenti/i })).toBeInTheDocument()
    })
  })
})
