import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { RequestSignatureModal } from '../RequestSignatureModal'

vi.mock('../../../services/userService', () => ({
  getUsers: vi.fn().mockResolvedValue({ results: [{ id: 'u1', email: 's@test.com' }] }),
}))

vi.mock('../../../services/signatureService', () => ({
  requestForProtocol: vi.fn(),
  requestForDossier: vi.fn(),
}))

describe('RequestSignatureModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders Richiedi firma and format options', async () => {
    render(
      <RequestSignatureModal
        open
        targetType="protocol"
        targetId="p1"
        onClose={() => {}}
        onSuccess={() => {}}
      />,
    )
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Richiedi firma/i })).toBeInTheDocument()
    })
    expect(screen.getByText(/CAdES/i)).toBeInTheDocument()
  })
})
