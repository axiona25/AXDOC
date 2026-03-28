import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { VideoPlayer } from '../VideoPlayer'

describe('VideoPlayer', () => {
  it('renders video element with src', () => {
    render(<VideoPlayer url="/v.mp4" mimeType="video/mp4" fileName="clip.mp4" />)
    const v = document.querySelector('video')
    expect(v).toHaveAttribute('src', '/v.mp4')
  })

  it('shows download button when onDownload set', () => {
    render(<VideoPlayer url="/v.webm" onDownload={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Scarica/i })).toBeInTheDocument()
  })
})
