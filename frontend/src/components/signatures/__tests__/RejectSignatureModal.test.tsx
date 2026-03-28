import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RejectSignatureModal } from '../RejectSignatureModal'

describe('RejectSignatureModal', () => {
  it('renders title and Rifiuta button', () => {
    render(<RejectSignatureModal onClose={() => {}} onReject={vi.fn()} />)
    expect(screen.getByRole('heading', { name: /Rifiuta firma/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Rifiuta$/i })).toBeInTheDocument()
  })
})
