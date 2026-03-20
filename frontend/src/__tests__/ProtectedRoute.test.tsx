import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ProtectedRoute } from '../components/auth/ProtectedRoute'
import { useAuthStore } from '../store/authStore'

vi.mock('../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

function TestProtected({ allowedRoles }: { allowedRoles?: import('../types/auth').UserRole[] }) {
  return (
    <ProtectedRoute allowedRoles={allowedRoles}>
      <div>Protected content</div>
    </ProtectedRoute>
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      setUser: vi.fn(),
      clearUser: vi.fn(),
      initializeAuth: vi.fn(),
    })
  })

  it('redirects to login when not authenticated', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      setUser: vi.fn(),
      clearUser: vi.fn(),
      initializeAuth: vi.fn(),
    })
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/dashboard" element={<TestProtected />} />
          <Route path="/login" element={<div>Login page</div>} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('Login page')).toBeInTheDocument()
  })

  it('renders children when authenticated', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: {
        id: '1',
        email: 'u@t.com',
        first_name: 'U',
        last_name: 'T',
        role: 'OPERATOR',
        avatar: null,
        phone: '',
        must_change_password: false,
      },
      isAuthenticated: true,
      isLoading: false,
      setUser: vi.fn(),
      clearUser: vi.fn(),
      initializeAuth: vi.fn(),
    })
    render(
      <MemoryRouter>
        <TestProtected />
      </MemoryRouter>
    )
    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })

  it('redirects to unauthorized when role not allowed', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: {
        id: '1',
        email: 'u@t.com',
        first_name: 'U',
        last_name: 'T',
        role: 'OPERATOR',
        avatar: null,
        phone: '',
        must_change_password: false,
      },
      isAuthenticated: true,
      isLoading: false,
      setUser: vi.fn(),
      clearUser: vi.fn(),
      initializeAuth: vi.fn(),
    })
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/admin" element={<TestProtected allowedRoles={['ADMIN']} />} />
          <Route path="/unauthorized" element={<div>Unauthorized</div>} />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('Unauthorized')).toBeInTheDocument()
  })
})
