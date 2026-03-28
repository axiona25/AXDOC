import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { OUFormModal } from '../OUFormModal'

const orgs = [
  { id: 'p1', name: 'Root', code: 'R', parent: null } as never,
]

describe('OUFormModal', () => {
  it('renders edit title when initial is set', () => {
    render(
      <OUFormModal
        isOpen
        onClose={vi.fn()}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
        initial={
          {
            id: 'o1',
            name: 'X',
            code: 'X',
            description: '',
            parent: null,
            is_active: true,
            created_at: '',
            updated_at: '',
          } as never
        }
        organizations={orgs}
      />,
    )
    expect(screen.getByRole('heading', { name: /Modifica unità organizzativa/i })).toBeInTheDocument()
  })

  it('renders new OU form fields', () => {
    render(
      <OUFormModal
        isOpen
        onClose={vi.fn()}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
        initial={null}
        organizations={orgs}
      />,
    )
    expect(screen.getByRole('heading', { name: /Nuova unità organizzativa/i })).toBeInTheDocument()
    expect(screen.getByText(/^Nome$/i)).toBeInTheDocument()
    expect(screen.getByText(/Codice \(univoco\)/i)).toBeInTheDocument()
  })
})
