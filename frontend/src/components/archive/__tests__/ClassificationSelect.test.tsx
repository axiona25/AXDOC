import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ClassificationSelect } from '../ClassificationSelect'

vi.mock('../../../services/archiveService', () => ({
  getTitolario: vi.fn().mockResolvedValue([
    {
      children: [{ code: 'C1', label: 'Classe uno', retention: 10 }],
    },
  ]),
}))

describe('ClassificationSelect', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders classification input after load', async () => {
    const onChange = vi.fn()
    render(<ClassificationSelect value="" onChange={onChange} />)
    await waitFor(() => {
      expect(screen.queryByText(/Caricamento/i)).not.toBeInTheDocument()
    })
    expect(screen.getByPlaceholderText(/Seleziona classificazione/i)).toBeInTheDocument()
  })
})
