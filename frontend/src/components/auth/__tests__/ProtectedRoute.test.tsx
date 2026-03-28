import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ProtectedRoute } from '../ProtectedRoute'
import { useAuthStore } from '../../../store/authStore'

vi.mock('../../../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

vi.mock('../../layout/AuthenticatedLayout', () => ({
  AuthenticatedLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="layout">{children}</div>
  ),
}))

describe('ProtectedRoute (components/auth)', () => {
  beforeEach(() => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      setUser: vi.fn(),
      clearUser: vi.fn(),
      initializeAuth: vi.fn(),
    } as never)
  })

  it('redirects when not authenticated', () => {
    render(
      <MemoryRouter initialEntries={['/x']}>
        <Routes>
          <Route
            path="/x"
            element={
              <ProtectedRoute>
                <div>child</div>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>Login page</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Login page')).toBeInTheDocument()
  })

  it('shows children when authenticated', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: {
        id: '1',
        email: 'u@t.com',
        first_name: 'U',
        last_name: 'T',
        role: 'OPERATOR',
        avatar: null,
        phone: '',
      } as never,
      isAuthenticated: true,
      isLoading: false,
      setUser: vi.fn(),
      clearUser: vi.fn(),
      initializeAuth: vi.fn(),
    })
    render(
      <MemoryRouter initialEntries={['/x']}>
        <Routes>
          <Route
            path="/x"
            element={
              <ProtectedRoute>
                <div>child</div>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>Login page</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('child')).toBeInTheDocument()
    expect(screen.getByTestId('layout')).toBeInTheDocument()
  })
})
