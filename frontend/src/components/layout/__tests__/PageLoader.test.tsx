import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { PageLoader } from '../PageLoader'

describe('PageLoader', () => {
  it('renders root with min-height screen', () => {
    const { container } = render(<PageLoader />)
    expect(container.firstChild).toHaveClass('min-h-screen')
  })

  it('renders animated skeleton blocks', () => {
    const { container: c } = render(<PageLoader />)
    const pulse = c.querySelector('.animate-pulse')
    expect(pulse).toBeTruthy()
  })
})
