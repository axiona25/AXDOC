import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProtocolTable } from '../ProtocolTable'

const sample = {
  id: 'pr1',
  protocol_id: '2025/T1/0001',
  protocol_display: '2025/T1/0001',
  subject: 'Oggetto test',
  direction: 'in' as const,
  sender_receiver: 'Mario',
  organizational_unit_name: 'UO A',
  registered_at: '2025-06-01T10:00:00Z',
  category: 'file' as const,
  status: 'active' as const,
}

describe('ProtocolTable', () => {
  it('renders column headers', () => {
    render(
      <MemoryRouter>
        <ProtocolTable
          protocols={[]}
          directionFilter=""
          onDirectionFilterChange={() => {}}
          searchQuery=""
          onSearchChange={() => {}}
          onView={vi.fn()}
          onDownload={vi.fn()}
          onArchive={vi.fn()}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText('ID Protocollo')).toBeInTheDocument()
    expect(screen.getByText('Oggetto')).toBeInTheDocument()
    expect(screen.getByText('Mittente/Dest.')).toBeInTheDocument()
  })

  it('shows mock protocol row', () => {
    render(
      <MemoryRouter>
        <ProtocolTable
          protocols={[sample as never]}
          directionFilter=""
          onDirectionFilterChange={() => {}}
          searchQuery=""
          onSearchChange={() => {}}
          onView={vi.fn()}
          onDownload={vi.fn()}
          onArchive={vi.fn()}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText('Oggetto test')).toBeInTheDocument()
    expect(screen.getByText('IN')).toBeInTheDocument()
  })
})
