import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SkipLink } from '../SkipLink'

describe('SkipLink', () => {
  it('applies focus-visible classes for accessibility', () => {
    render(<SkipLink />)
    const link = screen.getByRole('link', { name: /Vai al contenuto principale/i })
    expect(link.className).toContain('indigo')
  })

  it('renders skip link to main content', () => {
    render(<SkipLink />)
    const link = screen.getByRole('link', { name: /Vai al contenuto principale/i })
    expect(link).toHaveAttribute('href', '#main-content')
  })
})
