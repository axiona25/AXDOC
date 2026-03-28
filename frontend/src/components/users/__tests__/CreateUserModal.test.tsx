import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CreateUserModal } from '../CreateUserModal'
import * as userService from '../../../services/userService'

vi.mock('../../../services/userService', () => ({
  createUserManual: vi.fn().mockResolvedValue({
    user: { email: 'new@test.com' },
    generated_password: 'GenPass99!',
    welcome_email_sent: false,
  }),
}))

const orgs = [{ id: 'ou-1', name: 'UO Test', code: 'T1', tenant: 't1' }]

describe('CreateUserModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(userService.createUserManual).mockResolvedValue({
      user: { email: 'new@test.com' } as never,
      generated_password: 'GenPass99!',
      welcome_email_sent: false,
    })
  })

  it('renders Nuovo utente and required fields', () => {
    render(
      <CreateUserModal
        isOpen
        onClose={() => {}}
        onSuccess={() => {}}
        organizations={orgs as never}
      />,
    )
    expect(screen.getByRole('heading', { name: /Nuovo utente/i })).toBeInTheDocument()
    expect(screen.getByText(/^Email \*$/i)).toBeInTheDocument()
    expect(screen.getByText(/^Nome \*$/i)).toBeInTheDocument()
    expect(screen.getByText(/^Cognome \*$/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Crea utente/i })).toBeInTheDocument()
  })

  it('submit with valid data calls createUserManual', async () => {
    const user = userEvent.setup()
    render(
      <CreateUserModal
        isOpen
        onClose={() => {}}
        onSuccess={() => {}}
        organizations={orgs as never}
      />,
    )
    const inputs = screen.getAllByRole('textbox')
    await user.type(inputs[0], 'new@test.com')
    await user.type(inputs[1], 'Anna')
    await user.type(inputs[2], 'Bianchi')
    await user.click(screen.getByRole('button', { name: /Crea utente/i }))
    await waitFor(() => {
      expect(userService.createUserManual).toHaveBeenCalled()
    })
    expect(userService.createUserManual).toHaveBeenCalledWith(
      expect.objectContaining({
        email: 'new@test.com',
        first_name: 'Anna',
        last_name: 'Bianchi',
      }),
    )
  })

  it('shows generated password after creation', async () => {
    const user = userEvent.setup()
    render(
      <CreateUserModal
        isOpen
        onClose={() => {}}
        onSuccess={() => {}}
        organizations={orgs as never}
      />,
    )
    const inputs = screen.getAllByRole('textbox')
    await user.type(inputs[0], 'new@test.com')
    await user.type(inputs[1], 'Anna')
    await user.type(inputs[2], 'Bianchi')
    await user.click(screen.getByRole('button', { name: /Crea utente/i }))
    await waitFor(() => {
      expect(screen.getByText('GenPass99!')).toBeInTheDocument()
    })
  })
})
