import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TextViewer } from '../TextViewer'

describe('TextViewer', () => {
  it('shows empty placeholder when content empty', () => {
    render(<TextViewer content="" />)
    expect(screen.getByText('(vuoto)')).toBeInTheDocument()
  })

  it('renders content in pre', () => {
    render(<TextViewer content="hello world" language="txt" />)
    expect(screen.getByText('hello world')).toBeInTheDocument()
  })

  it('shows Scarica with onDownload', () => {
    render(<TextViewer content="x" onDownload={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Scarica/i })).toBeInTheDocument()
  })
})
