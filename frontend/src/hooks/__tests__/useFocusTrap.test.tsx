import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useFocusTrap } from '../useFocusTrap'

function TrapHost({ active }: { active: boolean }) {
  const ref = useFocusTrap(active)
  return (
    <div ref={ref} data-testid="trap">
      <button type="button">Primo</button>
      <button type="button">Secondo</button>
    </div>
  )
}

describe('useFocusTrap', () => {
  it('cycles tab from last to first', async () => {
    const user = userEvent.setup()
    render(<TrapHost active />)
    const first = screen.getByRole('button', { name: 'Primo' })
    const second = screen.getByRole('button', { name: 'Secondo' })
    expect(document.activeElement).toBe(first)
    await user.tab()
    expect(document.activeElement).toBe(second)
    await user.tab()
    expect(document.activeElement).toBe(first)
  })
})
