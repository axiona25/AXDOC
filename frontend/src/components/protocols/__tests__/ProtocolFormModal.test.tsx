import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProtocolFormModal } from '../ProtocolFormModal'
import * as protocolService from '../../../services/protocolService'

vi.mock('../../../services/protocolService', () => ({
  createProtocolWithFile: vi.fn().mockResolvedValue({
    protocol_id: 'p1',
    registered_at: '2025-01-01T10:00:00Z',
  }),
}))

vi.mock('../../../services/organizationService', () => ({
  getOrganizationalUnits: vi.fn().mockResolvedValue({
    results: [{ id: 'ou-1', name: 'UO Test', code: 'T1', tenant: 't' }],
  }),
}))

vi.mock('../../../services/documentService', () => ({
  getDocuments: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../../services/mailService', () => ({
  getMailMessages: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../../services/dossierService', () => ({
  getDossiers: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../../services/userService', () => ({
  getUsers: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../../services/contactService', () => ({
  searchContacts: vi.fn().mockResolvedValue({ results: [] }),
}))

describe('ProtocolFormModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders Nuovo protocollo with oggetto and direzione', async () => {
    render(
      <ProtocolFormModal
        isOpen
        onClose={() => {}}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
      />,
    )
    expect(screen.getByRole('heading', { name: /Nuovo protocollo/i })).toBeInTheDocument()
    expect(screen.getByText(/^Oggetto \*$/i)).toBeInTheDocument()
    expect(screen.getByText(/^Direzione \*$/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /In entrata/i })).toBeInTheDocument()
  })

  it('submit on last step calls createProtocolWithFile', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(
      <ProtocolFormModal
        isOpen
        onClose={() => {}}
        onSubmit={onSubmit}
      />,
    )
    await user.type(screen.getByPlaceholderText(/Oggetto del protocollo/i), 'Test oggetto')
    await user.click(screen.getByRole('button', { name: /Avanti →/i }))
    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'ou-1')
    await user.click(screen.getByRole('button', { name: /Avanti →/i }))
    await user.click(screen.getByRole('button', { name: /Avanti →/i }))
    await user.click(screen.getByRole('button', { name: /Avanti →/i }))
    await user.click(screen.getByRole('button', { name: /Crea protocollo/i }))
    await waitFor(() => {
      expect(protocolService.createProtocolWithFile).toHaveBeenCalled()
    })
  })
})
