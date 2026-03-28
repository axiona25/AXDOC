import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { DailyRegisterPage } from '../DailyRegisterPage'

vi.mock('../../services/protocolService', () => ({
  getDailyRegister: vi.fn().mockResolvedValue({
    date: '2026-03-28',
    protocols: [],
  }),
}))

describe('DailyRegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders Registro giornaliero title and date input', async () => {
    render(
      <MemoryRouter>
        <DailyRegisterPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Registro giornaliero/i })).toBeInTheDocument()
    expect(document.querySelector('input[type="date"]')).toBeTruthy()
    await waitFor(() => {
      expect(screen.queryByText(/Caricamento/i)).not.toBeInTheDocument()
    })
  })

  it('shows print button', () => {
    render(
      <MemoryRouter>
        <DailyRegisterPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: /^Stampa$/i })).toBeInTheDocument()
  })

  it('shows link back to protocols', () => {
    render(
      <MemoryRouter>
        <DailyRegisterPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: /← Protocolli/i })).toBeInTheDocument()
  })
})
