import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EmailViewer } from '../EmailViewer'

describe('EmailViewer', () => {
  it('renders headers and body text', () => {
    render(
      <EmailViewer
        data={{
          from: 'a@x.com',
          to: 'b@x.com',
          subject: 'Hi',
          date: '2026-01-01',
          body_text: 'Body line',
        }}
      />,
    )
    expect(screen.getByText(/a@x\.com/)).toBeInTheDocument()
    expect(screen.getByText('Body line')).toBeInTheDocument()
  })

  it('shows Scarica when onDownload provided', () => {
    render(<EmailViewer data={{}} onDownload={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Scarica/i })).toBeInTheDocument()
  })
})
