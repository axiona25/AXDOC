import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { UploadModal } from '../UploadModal'

describe('UploadModal', () => {
  it('renders when open and has title and file area', () => {
    render(
      <UploadModal
        open
        onClose={vi.fn()}
        onUpload={vi.fn()}
        folders={[]}
      />
    )
    expect(screen.getByText(/Carica documento/i)).toBeDefined()
    expect(screen.getByPlaceholderText(/Titolo documento/i)).toBeDefined()
  })

  it('Carica button is disabled when no file selected', () => {
    render(
      <UploadModal
        open
        onClose={vi.fn()}
        onUpload={vi.fn()}
        folders={[]}
      />
    )
    const submitBtn = screen.getByRole('button', { name: /Carica/i })
    expect((submitBtn as HTMLButtonElement).disabled).toBe(true)
  })
})
