import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SettingsPage } from '../SettingsPage'

vi.mock('../../services/adminService', () => ({
  getSettings: vi.fn().mockResolvedValue({
    email: {},
    organization: {},
    protocol: {},
    security: {
      password_min_length: 8,
      password_require_uppercase: true,
      password_require_lowercase: true,
      password_require_digit: true,
      password_require_special: true,
      password_expiry_days: 0,
      password_history_count: 0,
      login_attempts: 5,
    },
    storage: {},
    ldap: {},
    conservation: {},
  }),
  patchSettings: vi.fn(),
  testEmail: vi.fn(),
  testLdap: vi.fn(),
}))


describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows email tab', async () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Email$/i })).toBeInTheDocument()
    })
  })

  it('renders impostazioni di sistema', async () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Impostazioni di sistema/i })).toBeInTheDocument()
    })
  })
})
