import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuthStore } from '../store/authStore'

const clearTokens = vi.fn()
const getAccessToken = vi.fn()

vi.mock('../services/api', () => ({
  clearTokens: (...a: unknown[]) => clearTokens(...a),
  getAccessToken: () => getAccessToken(),
  setTokens: vi.fn(),
}))

vi.mock('../services/authService', () => ({
  getMe: vi.fn().mockResolvedValue({
    id: '1',
    email: 'test@test.com',
    first_name: 'Test',
    last_name: 'User',
    role: 'OPERATOR',
    avatar: null,
    phone: '',
    must_change_password: false,
  }),
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
    clearTokens.mockClear()
    getAccessToken.mockReset()
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false })
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
    expect(clearTokens).toHaveBeenCalled()
  })

  it('initializeAuth with no token clears loading', async () => {
    getAccessToken.mockReturnValue(null)
    await useAuthStore.getState().initializeAuth()
    expect(useAuthStore.getState().isLoading).toBe(false)
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })

  it('initializeAuth with token loads user', async () => {
    getAccessToken.mockReturnValue('tok')
    await useAuthStore.getState().initializeAuth()
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
    expect(useAuthStore.getState().user?.email).toBe('test@test.com')
  })
})
