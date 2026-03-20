import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { EntityMetadataPanel } from '../EntityMetadataPanel'

vi.mock('../../../services/metadataService', () => ({
  getMetadataStructure: vi.fn(() => Promise.resolve({ id: 's1', name: 'Struttura', fields: [] })),
  getMetadataStructures: vi.fn(() => Promise.resolve({ results: [{ id: 's1', name: 'Struttura', fields: [] }] })),
  updateFolderMetadata: vi.fn(() => Promise.resolve({})),
  updateDossierMetadata: vi.fn(() => Promise.resolve({})),
}))

describe('EntityMetadataPanel', () => {
  it('renders in read-only when no structure assigned', () => {
    render(
      <EntityMetadataPanel
        entityType="dossier"
        entityId="e1"
        metadataStructureId={null}
        metadataValues={{}}
        canEdit={true}
      />
    )
    expect(screen.getByText(/Nessuna struttura metadati assegnata/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Assegna struttura/ })).toBeInTheDocument()
  })

  it('renders assign button only when canEdit', () => {
    render(
      <EntityMetadataPanel
        entityType="dossier"
        entityId="e1"
        metadataStructureId={null}
        metadataValues={{}}
        canEdit={false}
      />
    )
    expect(screen.getByText(/Nessuna struttura metadati assegnata/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Assegna struttura/ })).not.toBeInTheDocument()
  })

  it('renders Modifica when structure assigned and canEdit', async () => {
    render(
      <EntityMetadataPanel
        entityType="dossier"
        entityId="e1"
        metadataStructureId="s1"
        metadataValues={{ foo: 'bar' }}
        canEdit={true}
        onSave={vi.fn()}
      />
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Modifica/ })).toBeInTheDocument()
    })
  })
})
