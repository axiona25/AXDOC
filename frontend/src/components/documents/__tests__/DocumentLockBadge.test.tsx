import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DocumentLockBadge } from '../DocumentLockBadge'

describe('DocumentLockBadge', () => {
  it('returns null when not locked', () => {
    const { container } = render(
      <DocumentLockBadge lockedBy={null} isCurrentUser={false} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('shows lock without unlock for other user', () => {
    render(
      <DocumentLockBadge
        lockedBy={{ id: 'u2', email: 'other@test.com' }}
        isCurrentUser={false}
      />,
    )
    expect(screen.getByText(/Bloccato da other@test\.com/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Sblocca/i })).not.toBeInTheDocument()
  })

  it('shows lock message and unlock for current user', async () => {
    const user = userEvent.setup()
    const onUnlock = vi.fn()
    render(
      <DocumentLockBadge
        lockedBy={{ id: 'u1', first_name: 'Ada', last_name: 'Lovelace' }}
        isCurrentUser
        onUnlock={onUnlock}
      />,
    )
    expect(screen.getByText(/Bloccato da Ada Lovelace/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Sblocca/i }))
    expect(onUnlock).toHaveBeenCalled()
  })
})
