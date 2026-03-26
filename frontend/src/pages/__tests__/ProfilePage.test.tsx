import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProfilePage } from '../ProfilePage'

vi.mock('../../store/authStore', () => {
  const initializeAuth = vi.fn()
  const store = vi.fn((sel: (s: unknown) => unknown) =>
    sel({
      user: {
        id: '1',
        email: 'u@test.com',
        first_name: 'Mario',
        last_name: 'Rossi',
        role: 'OPERATOR',
        mfa_enabled: false,
      },
    }),
  )
  return {
    useAuthStore: Object.assign(store, {
      getState: () => ({ initializeAuth }),
    }),
  }
})

vi.mock('../../services/authService', () => ({
  disableMFA: vi.fn(),
}))

vi.mock('../../components/auth/MFASetupWizard', () => ({
  MFASetupWizard: () => null,
}))

vi.mock('../../components/auth/LDAPStatusCard', () => ({
  LDAPStatusCard: () => null,
}))

describe('ProfilePage', () => {
  it('renders profilo and user name', () => {
    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /^Profilo$/i })).toBeInTheDocument()
    expect(screen.getByText(/Mario/)).toBeInTheDocument()
  })
})
