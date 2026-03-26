import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { OCRStatusBadge } from '../OCRStatusBadge'

describe('OCRStatusBadge', () => {
  it('pending shows waiting label', () => {
    render(<OCRStatusBadge status="pending" />)
    expect(screen.getByText(/OCR in attesa/i)).toBeInTheDocument()
  })

  it('completed shows green label', () => {
    render(<OCRStatusBadge status="completed" confidence={90} />)
    expect(screen.getByText(/Testo estratto/)).toBeInTheDocument()
    expect(screen.getByText(/90%/)).toBeInTheDocument()
  })

  it('failed shows error label', () => {
    render(<OCRStatusBadge status="failed" error="Errore OCR lungo da mostrare" />)
    expect(screen.getByText(/OCR fallito/)).toBeInTheDocument()
  })

  it('processing shows spinner', () => {
    render(<OCRStatusBadge status="processing" />)
    expect(screen.getByText(/OCR in corso/)).toBeInTheDocument()
  })
})
