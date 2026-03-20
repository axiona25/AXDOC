import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ArchivePage } from '../ArchivePage'

vi.mock('../../services/archiveService', () => ({
  getArchiveDocuments: vi.fn().mockResolvedValue([]),
  getPackages: vi.fn().mockResolvedValue([]),
  getRetentionRules: vi.fn().mockResolvedValue([]),
}))

describe('ArchivePage', () => {
  it('renders archive page', async () => {
    render(<ArchivePage />)
    expect(screen.getByText(/Archivio Documentale/)).toBeInTheDocument()
  })

  it('shows tab corrente, deposito, storico', () => {
    render(<ArchivePage />)
    expect(screen.getByText('Archivio Corrente')).toBeInTheDocument()
    expect(screen.getByText('Archivio di Deposito')).toBeInTheDocument()
    expect(screen.getByText('Archivio Storico')).toBeInTheDocument()
  })

  it('shows Pacchetti Informativi and Massimario tabs', () => {
    render(<ArchivePage />)
    expect(screen.getByText('Pacchetti Informativi')).toBeInTheDocument()
    expect(screen.getByText('Massimario di scarto')).toBeInTheDocument()
  })
})
