import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ResetPasswordPage } from '../ResetPasswordPage'

vi.mock('../../services/authService', () => ({
  confirmPasswordReset: vi.fn().mockResolvedValue(undefined),
}))

describe('ResetPasswordPage', () => {
  it('renders nuova password heading', () => {
    render(
      <MemoryRouter initialEntries={['/reset-password/tok123']}>
        <Routes>
          <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Nuova password/i })).toBeInTheDocument()
  })
})
