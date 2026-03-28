import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { InviteUserModal } from '../InviteUserModal'
import * as userService from '../../../services/userService'

vi.mock('../../../services/userService', () => ({
  inviteUser: vi.fn().mockResolvedValue({}),
}))

vi.mock('../../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({
      user: { id: '1', email: 'admin@test.com', role: 'ADMIN' },
      isAuthenticated: true,
    }),
  ),
}))

const orgs = [{ id: 'ou-1', name: 'UO Test', code: 'T1', tenant: 't1' }]

describe('InviteUserModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders Invita utente', () => {
    render(
      <InviteUserModal
        isOpen
        onClose={() => {}}
        onSuccess={() => {}}
        organizations={orgs as never}
      />,
    )
    expect(screen.getByRole('heading', { name: /Invita utente/i })).toBeInTheDocument()
  })

  it('has email field', () => {
    render(
      <InviteUserModal
        isOpen
        onClose={() => {}}
        onSuccess={() => {}}
        organizations={orgs as never}
      />,
    )
    expect(screen.getByText(/^Email$/i)).toBeInTheDocument()
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('submit calls inviteUser', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()
    render(
      <InviteUserModal
        isOpen
        onClose={() => {}}
        onSuccess={onSuccess}
        organizations={orgs as never}
      />,
    )
    await user.type(screen.getByRole('textbox'), 'invite@test.com')
    await user.click(screen.getByRole('button', { name: /Invia invito/i }))
    await waitFor(() => {
      expect(userService.inviteUser).toHaveBeenCalled()
    })
    expect(userService.inviteUser).toHaveBeenCalledWith(
      expect.objectContaining({ email: 'invite@test.com' }),
    )
  })
})
