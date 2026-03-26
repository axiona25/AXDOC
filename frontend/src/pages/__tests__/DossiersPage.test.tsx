import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { DossiersPage } from '../DossiersPage'

vi.mock('../../services/dossierService', () => ({
  getDossiers: vi.fn().mockResolvedValue({ results: [] }),
  getDossier: vi.fn(),
  updateDossier: vi.fn(),
  archiveDossier: vi.fn(),
  deleteDossier: vi.fn(),
}))

vi.mock('../../services/exportService', () => ({
  exportDossiersExcel: vi.fn(),
  exportDossiersPdf: vi.fn(),
}))

vi.mock('../../services/signatureService', () => ({
  getSignaturesByTarget: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../services/userService', () => ({
  getUsers: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../services/organizationService', () => ({
  getOrganizationalUnits: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../components/dossiers/DossierFormModal', () => ({
  DossierFormModal: () => null,
}))

vi.mock('../../components/dossiers/DossierCreateWizard', () => ({
  DossierCreateWizard: () => null,
}))

describe('DossiersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders fascicoli heading', async () => {
    render(
      <MemoryRouter>
        <DossiersPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /^Fascicoli$/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText('Caricamento...')).not.toBeInTheDocument()
    })
  })

  it('shows new dossier button', async () => {
    render(
      <MemoryRouter>
        <DossiersPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Nuovo fascicolo/i })).toBeInTheDocument()
    })
  })
})
