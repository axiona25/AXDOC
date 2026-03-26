import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NotificationBell } from '../NotificationBell'
import { useNotificationRealtimeStore } from '../../../store/notificationRealtimeStore'

vi.mock('../../../services/notificationService', () => ({
  getUnreadCount: vi.fn().mockResolvedValue({ count: 2 }),
  pollUnreadCount: vi.fn().mockResolvedValue({ unread_count: 2 }),
}))

vi.mock('../../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({ isAuthenticated: true, isLoading: false }),
  ),
}))

vi.mock('../NotificationWsContext', () => ({
  useNotificationWs: () => ({
    isConnected: true,
    markRead: vi.fn(),
    markAllRead: vi.fn(),
  }),
}))

vi.mock('../NotificationPanel', () => ({
  NotificationPanel: () => <div data-testid="panel">Panel</div>,
}))

describe('NotificationBell', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useNotificationRealtimeStore.setState({ unreadCount: 0, wsConnected: false })
  })

  it('renders bell and badge when count > 0', async () => {
    render(<NotificationBell />)
    expect(screen.getByRole('button', { name: /Notifiche/i })).toBeInTheDocument()
    expect(await screen.findByText('2')).toBeInTheDocument()
  })

  it('opens panel on click', async () => {
    const user = userEvent.setup()
    render(<NotificationBell />)
    await user.click(screen.getByRole('button', { name: /Notifiche/i }))
    expect(screen.getByTestId('panel')).toBeInTheDocument()
  })
})
