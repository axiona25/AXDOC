import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { P7MVerifyPage } from '../P7MVerifyPage'

describe('P7MVerifyPage', () => {
  it('renders Verifica firma P7M heading and file picker', () => {
    render(
      <MemoryRouter>
        <P7MVerifyPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Verifica firma P7M/i })).toBeInTheDocument()
    expect(screen.getByText(/Scegli file \.p7m/i)).toBeInTheDocument()
    expect(screen.getByText(/Nessun file selezionato/i)).toBeInTheDocument()
  })

  it('shows dashboard link', () => {
    render(
      <MemoryRouter>
        <P7MVerifyPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: /← Dashboard/i })).toBeInTheDocument()
  })
})
