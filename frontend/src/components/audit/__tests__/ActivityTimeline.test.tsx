import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { ActivityTimeline } from '../ActivityTimeline'
import type { AuditLogItem } from '../../../services/auditService'

const baseItem = (overrides: Partial<AuditLogItem>): AuditLogItem => ({
  id: '1',
  user_id: 'u1',
  user_email: 'user@test.com',
  action: 'DOCUMENT_CREATED',
  detail: {},
  ip_address: null,
  timestamp: '2026-03-28T14:30:00.000Z',
  ...overrides,
})

describe('ActivityTimeline', () => {
  it('renders empty state message', () => {
    render(<ActivityTimeline items={[]} />)
    expect(screen.getByText(/Nessuna attività recente/i)).toBeInTheDocument()
  })

  it('renders a list when items are present', () => {
    render(<ActivityTimeline items={[baseItem({ id: 'a' })]} />)
    expect(screen.getByRole('list')).toBeInTheDocument()
    expect(screen.getByRole('listitem')).toBeInTheDocument()
  })

  it('shows action label, user and timestamp per event', () => {
    render(<ActivityTimeline items={[baseItem({ id: 'e1' })]} />)
    const row = screen.getByRole('listitem')
    expect(within(row).getByText('user@test.com')).toBeInTheDocument()
    expect(within(row).getByText(/Documento creato/)).toBeInTheDocument()
    expect(row.textContent).toMatch(/\d{1,2}[/.]\d{1,2}[/.]\d{2,4}/)
    expect(row.textContent).toMatch(/\d{1,2}:\d{2}/)
  })

  it('shows Sistema when user_email is null', () => {
    render(<ActivityTimeline items={[baseItem({ user_email: null, action: 'LOGIN' })]} />)
    const row = screen.getByRole('listitem')
    expect(within(row).getByText('Sistema')).toBeInTheDocument()
    expect(within(row).getByText(/Accesso/)).toBeInTheDocument()
  })

  it('uses version label for DOCUMENT_UPLOADED when detail.version is set', () => {
    render(
      <ActivityTimeline
        items={[
          baseItem({
            action: 'DOCUMENT_UPLOADED',
            detail: { version: 3 },
          }),
        ]}
      />,
    )
    const row = screen.getByRole('listitem')
    expect(within(row).getByText(/Versione 3 caricata/)).toBeInTheDocument()
  })

  it('shows distinct labels for different action types (mapping per tipo)', () => {
    const { container } = render(
      <ActivityTimeline
        items={[
          baseItem({ id: '1', action: 'DOCUMENT_CREATED' }),
          baseItem({ id: '2', action: 'WORKFLOW_REJECTED', user_email: 'other@test.com' }),
        ]}
      />,
    )
    expect(container.textContent).toContain('Documento creato')
    expect(container.textContent).toContain('Documento rifiutato')
    expect(screen.getAllByText(/Documento creato/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Documento rifiutato/).length).toBeGreaterThanOrEqual(1)
  })
})
