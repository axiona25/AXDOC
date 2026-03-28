import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AudioPlayer } from '../AudioPlayer'

describe('AudioPlayer', () => {
  it('renders audio element and filename', () => {
    render(<AudioPlayer url="/a.mp3" fileName="song.mp3" />)
    expect(screen.getByText('song.mp3')).toBeInTheDocument()
    expect(document.querySelector('audio')).toHaveAttribute('src', '/a.mp3')
  })

  it('shows download with handler', () => {
    render(<AudioPlayer url="/a.wav" onDownload={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Scarica/i })).toBeInTheDocument()
  })
})
