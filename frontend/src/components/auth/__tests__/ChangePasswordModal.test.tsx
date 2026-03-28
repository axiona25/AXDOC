import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChangePasswordModal } from '../ChangePasswordModal'

vi.mock('../../../services/authService', () => ({
  changePasswordRequired: vi.fn().mockResolvedValue({}),
}))

describe('ChangePasswordModal', () => {
  it('renders new password fields and submit', () => {
    render(<ChangePasswordModal isOpen onSuccess={() => {}} />)
    expect(screen.getByText(/Nuova password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Cambia password/i })).toBeInTheDocument()
  })
})
