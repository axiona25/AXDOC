import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NotificationWsProvider } from '../NotificationWsContext'

vi.mock('../../../hooks/useNotificationWebSocket', () => ({
  useNotificationWebSocket: () => ({
    isConnected: false,
    markRead: vi.fn(),
    markAllRead: vi.fn(),
  }),
}))

vi.mock('../../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({ isAuthenticated: false, isLoading: false }),
  ),
}))

vi.mock('../../../store/toastStore', () => ({
  useToastStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({
      addToast: vi.fn(),
      clearAll: vi.fn(),
    }),
  ),
}))

vi.mock('../../../store/notificationRealtimeStore', () => ({
  useNotificationRealtimeStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({
      setUnreadCount: vi.fn(),
      setWsConnected: vi.fn(),
    }),
  ),
}))

describe('NotificationWsProvider', () => {
  it('renders children without crashing', () => {
    render(
      <NotificationWsProvider>
        <div>inside</div>
      </NotificationWsProvider>,
    )
    expect(screen.getByText('inside')).toBeInTheDocument()
  })
})
