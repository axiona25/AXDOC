import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MFAVerifyModal } from '../MFAVerifyModal'

vi.mock('../../../services/authService', () => ({
  verifyMFA: vi.fn(),
}))

describe('MFAVerifyModal', () => {
  it('renders verify heading', () => {
    render(
      <MFAVerifyModal
        open
        mfaPendingToken="tok"
        onSuccess={vi.fn()}
        onClose={() => {}}
      />,
    )
    expect(screen.getByText(/Verifica in due passaggi/i)).toBeInTheDocument()
  })
})
