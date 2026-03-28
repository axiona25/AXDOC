import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BreadcrumbProvider, useBreadcrumbTitle } from '../BreadcrumbContext'

function Consumer() {
  const { entityTitle, setEntityTitle } = useBreadcrumbTitle()
  return (
    <div>
      <span data-testid="ent">{entityTitle ?? 'none'}</span>
      <button type="button" onClick={() => setEntityTitle('Doc X')}>
        set title
      </button>
    </div>
  )
}

describe('BreadcrumbContext', () => {
  it('provider exposes entity title to consumer', async () => {
    const user = userEvent.setup()
    render(
      <BreadcrumbProvider>
        <Consumer />
      </BreadcrumbProvider>,
    )
    expect(screen.getByTestId('ent')).toHaveTextContent('none')
    await user.click(screen.getByRole('button', { name: /set title/i }))
    expect(screen.getByTestId('ent')).toHaveTextContent('Doc X')
  })
})
