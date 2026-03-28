import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ShareListPanel } from '../ShareListPanel'

describe('ShareListPanel', () => {
  it('shows empty message', () => {
    render(
      <ShareListPanel shares={[]} onRevoke={() => {}} onNewShare={() => {}} />,
    )
    expect(screen.getByText(/Nessuna condivisione/i)).toBeInTheDocument()
  })

  it('lists share', () => {
    render(
      <ShareListPanel
        shares={[
          {
            id: 's1',
            recipient_display: 'a@b.com',
            recipient_type: 'external',
            is_valid: true,
            is_active: true,
            expires_at: null,
          } as never,
        ]}
        onRevoke={vi.fn()}
        onNewShare={vi.fn()}
      />,
    )
    expect(screen.getByText('a@b.com')).toBeInTheDocument()
  })
})
