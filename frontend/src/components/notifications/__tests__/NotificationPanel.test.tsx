import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { NotificationPanel } from '../NotificationPanel'

vi.mock('../../../services/notificationService', () => ({
  getNotifications: vi.fn().mockResolvedValue({ results: [] }),
  markRead: vi.fn(),
  getNotification: vi.fn(),
}))

describe('NotificationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows mark all read button', async () => {
    render(
      <MemoryRouter>
        <NotificationPanel onClose={vi.fn()} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: /Segna tutte come lette/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText(/Nessuna notifica/i)).toBeInTheDocument()
    })
  })

  it('shows heading and empty state', async () => {
    render(
      <MemoryRouter>
        <NotificationPanel onClose={vi.fn()} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Notifiche/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText(/Nessuna notifica/i)).toBeInTheDocument()
    })
  })
})
