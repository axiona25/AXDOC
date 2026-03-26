import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useNotificationWebSocket } from '../useNotificationWebSocket'

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({ isAuthenticated: true, isLoading: false }),
  ),
}))

vi.mock('../../services/api', () => ({
  getAccessToken: vi.fn(() => 'fake.jwt.token'),
}))

describe('useNotificationWebSocket', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'WebSocket',
      class {
        static OPEN = 1
        url: string
        onopen: (() => void) | null = null
        constructor(url: string) {
          this.url = url
          queueMicrotask(() => {
            this.onopen?.()
          })
        }
        close() {}
        send() {}
      } as unknown as typeof WebSocket,
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('connects when enabled and token present', async () => {
    const { result } = renderHook(() =>
      useNotificationWebSocket({ enabled: true, onConnectionChange: vi.fn() }),
    )
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
  })
})
