import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NotificationItemView } from '../NotificationItem'

describe('NotificationItemView', () => {
  it('shows title, body and triggers onClick', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(
      <NotificationItemView
        notification={{
          id: 'n1',
          title: 'Hello',
          body: 'World message',
          is_read: false,
          read_at: null,
          created_at: new Date().toISOString(),
          notification_type: 'info',
          link_url: '',
          metadata: {},
        }}
        onClick={onClick}
      />,
    )
    expect(screen.getByText('Hello')).toBeInTheDocument()
    expect(screen.getByText(/World message/)).toBeInTheDocument()
    await user.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalled()
  })
})
