import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ForgotPasswordPage } from '../ForgotPasswordPage'

vi.mock('../../services/authService', () => ({
  requestPasswordReset: vi.fn().mockResolvedValue(undefined),
}))

describe('ForgotPasswordPage', () => {
  it('renders recupero password heading', () => {
    render(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Recupero password/i })).toBeInTheDocument()
  })
})
