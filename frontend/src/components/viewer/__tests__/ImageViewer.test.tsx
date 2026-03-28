import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ImageViewer } from '../ImageViewer'

describe('ImageViewer', () => {
  it('renders zoom controls and image', () => {
    render(<ImageViewer url="/img.png" fileName="x.png" />)
    expect(screen.getByText(/100%/)).toBeInTheDocument()
    expect(document.querySelector('img')).toHaveAttribute('src', '/img.png')
  })

  it('shows download when onDownload provided', () => {
    render(<ImageViewer url="/a.jpg" onDownload={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Scarica/i })).toBeInTheDocument()
  })
})
