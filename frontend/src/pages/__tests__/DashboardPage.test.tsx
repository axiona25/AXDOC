import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { DashboardPage } from '../DashboardPage'

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({
      user: {
        id: '1',
        email: 'admin@test.com',
        role: 'ADMIN',
        first_name: 'Admin',
        last_name: 'Test',
      },
      isAuthenticated: true,
      isLoading: false,
    }),
  ),
}))

vi.mock('../../services/authService', () => ({
  logout: vi.fn(),
}))

vi.mock('../../services/notificationService', () => ({
  getUnreadCount: vi.fn().mockResolvedValue({ count: 0 }),
  pollUnreadCount: vi.fn(),
}))

vi.mock('../../components/notifications/NotificationWsContext', () => ({
  useNotificationWs: () => ({
    isConnected: false,
    markRead: vi.fn(),
    markAllRead: vi.fn(),
  }),
  NotificationWsProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('../../services/dashboardService', () => ({
  getDashboardStats: vi.fn().mockResolvedValue({
    total_users: 1,
    total_documents: 2,
    total_dossiers: { open: 1, archived: 0 },
    total_protocols: { count: 3, this_month: 1 },
    documents_by_status: { DRAFT: 1, APPROVED: 1 },
  }),
  getRecentDocuments: vi.fn().mockResolvedValue({ results: [] }),
  getMyTasks: vi.fn().mockResolvedValue({ results: [] }),
  getDocumentsTrend: vi.fn().mockResolvedValue({ results: [] }),
  getProtocolsTrend: vi.fn().mockResolvedValue({ results: [] }),
  getWorkflowStats: vi.fn().mockResolvedValue({
    active: 0,
    completed_total: 0,
    completed_this_month: 0,
    rejected: 0,
    cancelled: 0,
    avg_completion_hours: null,
  }),
  getStorageTrend: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('recharts', () => {
  const Box = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>
  return {
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
    BarChart: Box,
    Bar: () => null,
    XAxis: () => null,
    YAxis: () => null,
    Tooltip: () => null,
    Legend: () => null,
    LineChart: Box,
    Line: () => null,
    PieChart: Box,
    Pie: () => null,
    Cell: () => null,
    CartesianGrid: () => null,
  }
})

vi.mock('../../components/chat/ChatPanel', () => ({
  ChatPanel: () => null,
}))

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders dashboard title', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /AXDOC — Dashboard/i })).toBeInTheDocument()
  })

  it('shows nav link to protocols', () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: /^Protocolli$/i })).toBeInTheDocument()
  })

  it('shows StatsCard and recent documents section after load', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getAllByText('Utenti').length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('Documenti recenti')).toBeInTheDocument()
    })
  })
})
