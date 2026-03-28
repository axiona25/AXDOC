import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ChatPanel } from '../ChatPanel'

vi.mock('../../../services/chatService', () => ({
  getChatRooms: vi.fn().mockResolvedValue([]),
  getUnreadCount: vi.fn().mockResolvedValue({ count: 0 }),
}))

describe('ChatPanel', () => {
  it('shows empty state', async () => {
    render(<ChatPanel open onClose={() => {}} />)
    await waitFor(() => {
      expect(screen.getByText(/Nessuna chat/i)).toBeInTheDocument()
    })
  })
})
