import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NotificationToastContainer } from '../NotificationToast'

describe('NotificationToastContainer', () => {
  it('renders toast title and message', () => {
    const toast = {
      id: 't1',
      title: 'Avviso test',
      message: 'Dettaglio',
      notification_type: 'info',
      link_url: '',
      timestamp: Date.now(),
    }
    render(
      <NotificationToastContainer toasts={[toast]} onDismiss={vi.fn()} onNavigate={vi.fn()} />,
    )
    expect(screen.getByText('Avviso test')).toBeInTheDocument()
    expect(screen.getByText('Dettaglio')).toBeInTheDocument()
  })
})
