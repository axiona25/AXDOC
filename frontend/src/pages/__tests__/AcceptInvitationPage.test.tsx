import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AcceptInvitationPage } from '../AcceptInvitationPage'

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('../../services/api', () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
  setTokens: vi.fn(),
}))

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({
      setUser: vi.fn(),
    }),
  ),
}))

describe('AcceptInvitationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGet.mockResolvedValue({ data: { email: 'invite@test.com' } })
  })

  it('shows invalid link when token is missing', () => {
    render(
      <MemoryRouter initialEntries={['/accept-invitation']}>
        <Routes>
          <Route path="/accept-invitation" element={<AcceptInvitationPage />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText(/Link non valido/i)).toBeInTheDocument()
  })

  it('shows error when invitation fetch fails', async () => {
    mockGet.mockRejectedValueOnce(new Error('bad'))
    render(
      <MemoryRouter initialEntries={['/accept-invitation/bad']}>
        <Routes>
          <Route path="/accept-invitation/:token" element={<AcceptInvitationPage />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(/Invito non valido o scaduto/i)).toBeInTheDocument()
    })
  })

  it('after load shows Accetta invito and form fields', async () => {
    render(
      <MemoryRouter initialEntries={['/accept-invitation/tok']}>
        <Routes>
          <Route path="/accept-invitation/:token" element={<AcceptInvitationPage />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Accetta invito/i })).toBeInTheDocument()
    })
    expect(screen.getByText(/invite@test\.com/)).toBeInTheDocument()
    expect(screen.getByText(/^Nome$/i)).toBeInTheDocument()
    expect(screen.getByText(/^Cognome$/i)).toBeInTheDocument()
    expect(document.querySelectorAll('input').length).toBeGreaterThanOrEqual(4)
    expect(screen.getByRole('button', { name: /Accetta e accedi/i })).toBeInTheDocument()
  })
})
