import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { VerificationResultModal } from '../VerificationResultModal'

describe('VerificationResultModal', () => {
  it('shows valid result', () => {
    render(
      <VerificationResultModal onClose={() => {}} result={{ valid: true }} />,
    )
    expect(screen.getByText(/Valida/i)).toBeInTheDocument()
  })

  it('shows invalid with error', () => {
    render(
      <VerificationResultModal onClose={() => {}} result={{ valid: false, error: 'x' }} />,
    )
    expect(screen.getByText(/Non valida/i)).toBeInTheDocument()
  })
})
