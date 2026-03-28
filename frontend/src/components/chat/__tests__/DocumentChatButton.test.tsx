import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DocumentChatButton } from '../DocumentChatButton'

vi.mock('../../../services/chatService', () => ({
  getDocumentChat: vi.fn().mockResolvedValue({
    id: 'r1',
    title: 'Chat doc',
    document: 'd1',
    other_participant_email: 'x@y.z',
  }),
}))

describe('DocumentChatButton', () => {
  it('renders Chat button', () => {
    render(<DocumentChatButton documentId="d1" />)
    expect(screen.getByRole('button', { name: /Chat/i })).toBeInTheDocument()
  })
})
