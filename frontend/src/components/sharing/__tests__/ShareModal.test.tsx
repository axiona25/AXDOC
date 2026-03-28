import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ShareModal } from '../ShareModal'

vi.mock('../../../services/userService', () => ({
  getUsers: vi.fn().mockResolvedValue({ results: [] }),
}))

describe('ShareModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders Condividi and submit', async () => {
    const share = vi.fn().mockResolvedValue({ url: 'https://x.test/l/1' })
    render(
      <ShareModal
        open
        onClose={() => {}}
        onSuccess={() => {}}
        shareDocument={share}
        targetId="d1"
        targetLabel="documento"
      />,
    )
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Condividi documento/i })).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /Condividi$/i })).toBeInTheDocument()
  })
})
