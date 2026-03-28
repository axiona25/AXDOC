import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { SSOCallbackPage } from '../SSOCallbackPage'

vi.mock('../../services/api', () => ({
  setTokens: vi.fn(),
}))

vi.mock('../../services/authService', () => ({
  getMe: vi.fn().mockResolvedValue({ id: '1', email: 'u@test.com' }),
}))

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({
      setUser: vi.fn(),
    }),
  ),
}))

describe('SSOCallbackPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows error message when error query param present', async () => {
    render(
      <MemoryRouter initialEntries={['/sso-callback?error=access_denied']}>
        <Routes>
          <Route path="/sso-callback" element={<SSOCallbackPage />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('access_denied')).toBeInTheDocument()
    })
    expect(screen.getByRole('link', { name: /Torna al login/i })).toBeInTheDocument()
  })

  it('shows loading text initially with token params', () => {
    render(
      <MemoryRouter initialEntries={['/sso-callback?access=a&refresh=r']}>
        <Routes>
          <Route path="/sso-callback" element={<SSOCallbackPage />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText(/Accesso in corso/i)).toBeInTheDocument()
  })

  it('shows missing params error when tokens absent', async () => {
    render(
      <MemoryRouter initialEntries={['/sso-callback']}>
        <Routes>
          <Route path="/sso-callback" element={<SSOCallbackPage />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(/Parametri di accesso mancanti/i)).toBeInTheDocument()
    })
  })
})
