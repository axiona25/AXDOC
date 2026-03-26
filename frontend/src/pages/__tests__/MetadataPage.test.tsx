import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MetadataPage } from '../MetadataPage'

vi.mock('../../services/metadataService', () => ({
  getMetadataStructures: vi.fn().mockResolvedValue({ results: [] }),
  getMetadataStructure: vi.fn(),
  createMetadataStructure: vi.fn(),
  updateMetadataStructure: vi.fn(),
  deleteMetadataStructure: vi.fn(),
}))

describe('MetadataPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows nuova struttura button', async () => {
    render(
      <MemoryRouter>
        <MetadataPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Nuova struttura/i })).toBeInTheDocument()
    })
  })

  it('renders strutture metadati', async () => {
    render(
      <MemoryRouter>
        <MetadataPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Strutture metadati/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText(/Caricamento/i)).not.toBeInTheDocument()
    })
  })
})
