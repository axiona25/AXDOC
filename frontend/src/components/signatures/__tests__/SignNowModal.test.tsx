import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SignNowModal } from '../SignNowModal'

const req = {
  id: 'sr1',
  status: 'pending',
} as never

describe('SignNowModal', () => {
  it('renders Firma documento', () => {
    render(<SignNowModal signatureRequest={req} onClose={() => {}} onSign={vi.fn()} />)
    expect(screen.getByRole('heading', { name: /Firma documento/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Firma$/i })).toBeInTheDocument()
  })
})
