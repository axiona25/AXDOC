import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BulkActionBar } from '../BulkActionBar'

describe('BulkActionBar', () => {
  it('shows count and deselect calls handler', async () => {
    const user = userEvent.setup()
    const onDeselectAll = vi.fn()
    render(
      <BulkActionBar
        count={2}
        onDeselectAll={onDeselectAll}
        actions={[{ label: 'Azione', icon: <span />, onClick: vi.fn() }]}
      />,
    )
    expect(screen.getByText(/2 elementi selezionati/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Deseleziona tutto/i }))
    expect(onDeselectAll).toHaveBeenCalled()
  })

  it('requireConfirm opens modal before running action', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(
      <BulkActionBar
        count={1}
        onDeselectAll={vi.fn()}
        actions={[
          {
            label: 'Elimina',
            icon: <span />,
            onClick,
            requireConfirm: true,
            confirmTitle: 'Sicuro?',
            confirmMessage: 'Operazione irreversibile.',
          },
        ]}
      />,
    )
    await user.click(screen.getByRole('button', { name: /^Elimina$/i }))
    expect(screen.getByText('Sicuro?')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /^Conferma$/i }))
    expect(onClick).toHaveBeenCalled()
  })
})
