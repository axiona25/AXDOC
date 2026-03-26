import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MailPage } from '../MailPage'
import { TestQueryProvider } from '../../test/queryWrapper'

vi.mock('../../services/mailService', () => ({
  getMailAccounts: vi.fn().mockResolvedValue([]),
  getMailMessages: vi.fn().mockResolvedValue({ results: [] }),
  getMailMessage: vi.fn(),
  sendMail: vi.fn(),
  markUnread: vi.fn(),
  toggleStar: vi.fn(),
  fetchMailNow: vi.fn(),
  linkToProtocol: vi.fn(),
  unlinkFromProtocol: vi.fn(),
}))

describe('MailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders posta views', async () => {
    render(
      <MemoryRouter>
        <TestQueryProvider>
          <MailPage />
        </TestQueryProvider>
      </MemoryRouter>,
    )
    expect(await screen.findByRole('button', { name: /Posta in arrivo/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Nuova email/i })).toBeInTheDocument()
  })
})
