import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { UnauthorizedPage } from '../UnauthorizedPage'

describe('UnauthorizedPage', () => {
  it('renders access denied message', () => {
    render(
      <MemoryRouter>
        <UnauthorizedPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Accesso non autorizzato/i })).toBeInTheDocument()
  })
})
