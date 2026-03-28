import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { DossierCreateWizard } from '../DossierCreateWizard'

vi.mock('../../../services/dossierService', () => ({
  createDossier: vi.fn().mockResolvedValue({ id: 'd1' }),
}))

vi.mock('../../../services/metadataService', () => ({
  getMetadataStructures: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../../services/userService', () => ({
  getUsers: vi.fn().mockResolvedValue({
    results: [{ id: 'u1', email: 'a@test.com', first_name: 'A', last_name: 'B' }],
  }),
}))

vi.mock('../../../services/organizationService', () => ({
  getOrganizationalUnits: vi.fn().mockResolvedValue({
    results: [{ id: 'ou1', name: 'UO', code: 'U1' }],
  }),
}))

vi.mock('../../../services/archiveService', () => ({
  getTitolario: vi.fn().mockResolvedValue([]),
}))

describe('DossierCreateWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders step 1 with title, responsabile, UO and Avanti', async () => {
    render(<DossierCreateWizard isOpen onClose={() => {}} onSuccess={() => {}} />)
    expect(screen.getByText(/Nuovo fascicolo — Step 1\/3/i)).toBeInTheDocument()
    expect(screen.getByText(/Oggetto \/ Titolo \*/i)).toBeInTheDocument()
    expect(screen.getByText(/^Responsabile \*$/i)).toBeInTheDocument()
    expect(screen.getByText(/^Unità organizzativa \*$/i)).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Avanti/i })).toBeInTheDocument()
    })
  })
})
