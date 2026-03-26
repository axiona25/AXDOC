import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConfirmModal } from '../ConfirmModal'

describe('ConfirmModal', () => {
  it('click conferma calls onConfirm', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(
      <ConfirmModal open title="Titolo" message="Messaggio demo" onConfirm={onConfirm} onCancel={onCancel} />,
    )
    await user.click(screen.getByRole('button', { name: /^Conferma$/i }))
    expect(onConfirm).toHaveBeenCalled()
  })

  it('click annulla calls onCancel', async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()
    render(<ConfirmModal open title="T" message="M" onConfirm={vi.fn()} onCancel={onCancel} />)
    await user.click(screen.getByRole('button', { name: /^Annulla$/i }))
    expect(onCancel).toHaveBeenCalled()
  })

  it('escape calls onCancel', async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()
    render(<ConfirmModal open title="T" message="M" onConfirm={vi.fn()} onCancel={onCancel} />)
    await user.keyboard('{Escape}')
    expect(onCancel).toHaveBeenCalled()
  })
})
