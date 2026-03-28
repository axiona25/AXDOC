import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EditUserModal } from '../EditUserModal'
import * as userService from '../../../services/userService'

vi.mock('../../../services/userService', () => ({
  updateUser: vi.fn().mockResolvedValue({}),
  resetUserPassword: vi.fn().mockResolvedValue({ generated_password: 'TempPass123!' }),
  getUserPermissions: vi.fn().mockResolvedValue(null),
  setUserPermission: vi.fn(),
  getUsers: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../../services/organizationService', () => ({
  getOrganizationalUnits: vi.fn().mockResolvedValue({ results: [] }),
  addMember: vi.fn(),
  removeMember: vi.fn(),
}))

vi.mock('../../../services/groupService', () => ({
  getGroups: vi.fn().mockResolvedValue({ results: [] }),
  getGroupMembers: vi.fn().mockResolvedValue([]),
  addGroupMembers: vi.fn(),
  removeGroupMember: vi.fn(),
}))

vi.mock('../../../services/documentService', () => ({
  getDocuments: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../../services/dossierService', () => ({
  getDossiers: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({
      user: { id: '1', email: 'admin@test.com', role: 'ADMIN' },
      isAuthenticated: true,
    }),
  ),
}))

const baseUser = {
  id: 'u1',
  email: 'user@test.com',
  first_name: 'Mario',
  last_name: 'Rossi',
  role: 'OPERATOR' as const,
  user_type: 'internal' as const,
  is_active: true,
}

describe('EditUserModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  it('renders title Modifica utente and shows nome, cognome, ruolo', async () => {
    render(
      <EditUserModal
        isOpen
        user={baseUser as never}
        onClose={() => {}}
        onSuccess={() => {}}
      />,
    )
    expect(screen.getByRole('heading', { name: /Modifica utente/i })).toBeInTheDocument()
    expect(screen.getByText('user@test.com')).toBeInTheDocument()
    expect(screen.getByText(/^Nome \*$/i)).toBeInTheDocument()
    expect(screen.getByText(/^Cognome \*$/i)).toBeInTheDocument()
    expect(screen.getByText(/^Ruolo \*$/i)).toBeInTheDocument()
    expect(screen.getByDisplayValue('Mario')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Rossi')).toBeInTheDocument()
  })

  it('shows Salva informazioni and Reimposta password', async () => {
    render(
      <EditUserModal
        isOpen
        user={baseUser as never}
        onClose={() => {}}
        onSuccess={() => {}}
      />,
    )
    expect(screen.getByRole('button', { name: /Salva informazioni/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Reimposta password/i })).toBeInTheDocument()
  })

  it('changing role updates selection', async () => {
    const user = userEvent.setup()
    render(
      <EditUserModal
        isOpen
        user={baseUser as never}
        onClose={() => {}}
        onSuccess={() => {}}
      />,
    )
    await user.click(screen.getByRole('button', { name: /^Amministratore$/i }))
    expect(screen.getByRole('button', { name: /^Amministratore$/i })).toHaveClass('border-indigo-500')
  })

  it('submit calls updateUser', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()
    render(
      <EditUserModal
        isOpen
        user={baseUser as never}
        onClose={() => {}}
        onSuccess={onSuccess}
      />,
    )
    const nomeInput = screen.getByDisplayValue('Mario')
    await user.clear(nomeInput)
    await user.type(nomeInput, 'Luigi')
    await user.click(screen.getByRole('button', { name: /Salva informazioni/i }))
    await waitFor(() => {
      expect(userService.updateUser).toHaveBeenCalled()
    })
    expect(userService.updateUser).toHaveBeenCalledWith(
      'u1',
      expect.objectContaining({
        first_name: 'Luigi',
        last_name: 'Rossi',
      }),
    )
  })
})
