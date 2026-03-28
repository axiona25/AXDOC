import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ChatWindow } from '../ChatWindow'

vi.mock('../../../services/chatService', () => ({
  getRoomMessages: vi.fn().mockResolvedValue({ results: [] }),
  sendMessage: vi.fn(),
}))

vi.mock('../../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: { user: { email: string } | null }) => unknown) =>
    sel({ user: { email: 'u@test.com' } as never }),
  ),
}))

const room = {
  id: 'r1',
  name: 'Room X',
  document: null,
  members: [],
} as never

describe('ChatWindow', () => {
  it('renders room title', async () => {
    render(<ChatWindow room={room} onBack={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText('Room X')).toBeInTheDocument()
    })
  })
})
