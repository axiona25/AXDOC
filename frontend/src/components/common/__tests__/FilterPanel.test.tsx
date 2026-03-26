import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { FilterPanel } from '../FilterPanel'

const fields = [
  { name: 'ou_id', label: 'Unità', type: 'select' as const, options: [{ value: 'a', label: 'OU A' }] },
  { name: 'date_from', label: 'Data da', type: 'date' as const },
]

describe('FilterPanel', () => {
  it('opens panel and shows apply and reset', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <FilterPanel fields={fields} />
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { name: /Filtri avanzati/i }))
    expect(screen.getByRole('button', { name: /^Applica$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Ripristina filtri/i })).toBeInTheDocument()
  })

  it('reset clears draft fields', async () => {
    const user = userEvent.setup()
    const onReset = vi.fn()
    render(
      <MemoryRouter>
        <FilterPanel fields={fields} onReset={onReset} />
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { name: /Filtri avanzati/i }))
    const dateInput = screen.getByLabelText(/Data da/i)
    await user.type(dateInput, '2025-01-01')
    await user.click(screen.getByRole('button', { name: /Ripristina filtri/i }))
    expect(onReset).toHaveBeenCalled()
  })
})
