import { create } from 'zustand'
import type { User } from '../types/auth'
import { getMe } from '../services/authService'
import { getAccessToken, clearTokens } from '../services/api'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  setUser: (user: User | null) => void
  clearUser: () => void
  initializeAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  setUser: (user) =>
    set({
      user,
      isAuthenticated: !!user,
    }),

  clearUser: () => {
    clearTokens()
    set({ user: null, isAuthenticated: false })
  },

  initializeAuth: async () => {
    set({ isLoading: true })
    const token = getAccessToken()
    if (!token) {
      set({ isLoading: false, user: null, isAuthenticated: false })
      return
    }
    try {
      const user = await getMe()
      set({ user, isAuthenticated: true, isLoading: false })
    } catch {
      clearTokens()
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },
}))
