import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { DossierFormModal } from '../DossierFormModal'

vi.mock('../../../services/metadataService', () => ({
  getMetadataStructures: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../../services/userService', () => ({
  getUsers: vi.fn().mockResolvedValue({ results: [] }),
}))

describe('DossierFormModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders titolo and base fields', async () => {
    render(
      <DossierFormModal isOpen onClose={() => {}} onSubmit={vi.fn().mockResolvedValue(undefined)} />,
    )
    await waitFor(() => {
      expect(screen.getByText(/Nuovo fascicolo/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/^Titolo \*$/i)).toBeInTheDocument()
  })
})
