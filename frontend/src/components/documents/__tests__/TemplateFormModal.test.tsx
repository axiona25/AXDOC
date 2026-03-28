import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { TemplateFormModal } from '../TemplateFormModal'

vi.mock('../../../services/documentService', () => ({
  getFolders: vi.fn().mockResolvedValue([]),
}))

vi.mock('../../../services/metadataService', () => ({
  getMetadataStructures: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../../services/workflowService', () => ({
  getWorkflowTemplates: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../../services/templateService', () => ({
  createTemplate: vi.fn(),
  updateTemplate: vi.fn(),
}))

describe('TemplateFormModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders Nuovo template and auto workflow checkbox', async () => {
    render(
      <TemplateFormModal open onClose={() => {}} onSaved={() => {}} />,
    )
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Nuovo template/i })).toBeInTheDocument()
    })
    expect(screen.getByText(/Avvia workflow automaticamente/i)).toBeInTheDocument()
  })
})
