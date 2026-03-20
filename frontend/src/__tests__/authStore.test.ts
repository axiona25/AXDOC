import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuthStore } from '../store/authStore'

vi.mock('../services/api', () => ({
  clearTokens: vi.fn(),
  getAccessToken: vi.fn(),
  setTokens: vi.fn(),
}))

const mockUser = {
  id: '1',
  email: 'test@test.com',
  first_name: 'Test',
  last_name: 'User',
  role: 'OPERATOR' as const,
  avatar: null,
  phone: '',
  must_change_password: false,
}

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isAuthenticated: false })
  })

  it('setUser sets user and isAuthenticated true', () => {
    useAuthStore.getState().setUser(mockUser)
    expect(useAuthStore.getState().user).toEqual(mockUser)
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
  })

  it('clearUser sets user null and isAuthenticated false', () => {
    useAuthStore.getState().setUser(mockUser)
    useAuthStore.getState().clearUser()
    expect(useAuthStore.getState().user).toBeNull()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })
})
