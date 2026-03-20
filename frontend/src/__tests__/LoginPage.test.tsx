import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { LoginPage } from '../pages/LoginPage'
import * as authService from '../services/authService'

vi.mock('../services/authService', () => ({
  login: vi.fn(),
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function renderLogin() {
  return render(
    <BrowserRouter>
      <LoginPage />
    </BrowserRouter>
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders login form', () => {
    renderLogin()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /accedi/i })).toBeInTheDocument()
  })

  it('calls login on submit with valid data', async () => {
    const user = userEvent.setup()
    vi.mocked(authService.login).mockResolvedValue({
      access: 'a',
      refresh: 'r',
      user: {
        id: '1',
        email: 'test@test.com',
        first_name: 'Test',
        last_name: 'User',
        role: 'OPERATOR',
        avatar: null,
        phone: '',
        must_change_password: false,
      },
      must_change_password: false,
    })
    renderLogin()
    await user.type(screen.getByLabelText(/email/i), 'test@test.com')
    await user.type(screen.getByLabelText(/password/i), 'password1')
    await user.click(screen.getByRole('button', { name: /accedi/i }))
    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith('test@test.com', 'password1')
    })
  })

  it('shows error on 401', async () => {
    const user = userEvent.setup()
    vi.mocked(authService.login).mockRejectedValue({ response: { status: 401 } })
    renderLogin()
    await user.type(screen.getByLabelText(/email/i), 'test@test.com')
    await user.type(screen.getByLabelText(/password/i), 'wrong12')
    await user.click(screen.getByRole('button', { name: /accedi/i }))
    await waitFor(() => {
      expect(screen.getByText(/email o password non corretti/i)).toBeInTheDocument()
    })
  })

  it('shows locked message on 423', async () => {
    const user = userEvent.setup()
    vi.mocked(authService.login).mockRejectedValue({
      response: {
        status: 423,
        data: { message: 'Account bloccato. Riprova dopo 15 minuti.' },
      },
    })
    renderLogin()
    await user.type(screen.getByLabelText(/email/i), 'test@test.com')
    await user.type(screen.getByLabelText(/password/i), 'wrong12')
    await user.click(screen.getByRole('button', { name: /accedi/i }))
    await waitFor(() => {
      expect(screen.getByText(/account bloccato/i)).toBeInTheDocument()
    })
  })
})
