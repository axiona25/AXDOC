import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ChangePasswordPage } from '../ChangePasswordPage'

vi.mock('../../services/authService', () => ({
  changePassword: vi.fn(),
}))

describe('ChangePasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders Cambio password and password fields', () => {
    render(
      <MemoryRouter>
        <ChangePasswordPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Cambio password/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/Password attuale/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^Nuova password$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Conferma nuova password/i)).toBeInTheDocument()
  })

  it('shows intro text', () => {
    render(
      <MemoryRouter>
        <ChangePasswordPage />
      </MemoryRouter>,
    )
    expect(screen.getByText(/Inserisci la password attuale e la nuova/i)).toBeInTheDocument()
  })

  it('shows submit button', () => {
    render(
      <MemoryRouter>
        <ChangePasswordPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: /Salva password/i })).toBeInTheDocument()
  })
})
