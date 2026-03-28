import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MetadataPreviewModal } from '../MetadataPreviewModal'

vi.mock('../../../services/metadataService', () => ({
  getStructureDocuments: vi.fn().mockResolvedValue([]),
}))

vi.mock('../DynamicMetadataForm', () => ({
  DynamicMetadataForm: () => <div data-testid="dyn-meta">form</div>,
}))

const structure = {
  id: 's1',
  name: 'Struttura A',
  fields: [],
  is_active: true,
} as never

describe('MetadataPreviewModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('has close button', async () => {
    const onClose = vi.fn()
    render(<MetadataPreviewModal open onClose={onClose} structure={structure} />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Chiudi/i })).toBeInTheDocument()
    })
  })

  it('renders preview title with structure name', async () => {
    render(<MetadataPreviewModal open onClose={vi.fn()} structure={structure} />)
    expect(screen.getByRole('heading', { name: /Anteprima — Struttura A/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByTestId('dyn-meta')).toBeInTheDocument()
    })
  })
})
