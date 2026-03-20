import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { SignaturePanel } from '../SignaturePanel'

vi.mock('../../../services/signatureService', () => ({
  getSignaturesByTarget: vi.fn().mockResolvedValue([]),
  signStep: vi.fn(),
  rejectStep: vi.fn(),
  downloadSigned: vi.fn(),
  verifySignatureValidity: vi.fn(),
}))

describe('SignaturePanel', () => {
  beforeEach(async () => {
    const mod = await import('../../../services/signatureService')
    vi.mocked(mod.getSignaturesByTarget).mockResolvedValue([])
  })

  it('renders panel without signatures', async () => {
    render(
      <SignaturePanel
        targetType="protocol"
        targetId="pid-1"
        canRequestSignature={true}
        currentUserId="user-1"
      />
    )
    await waitFor(() => {
      expect(screen.getByText(/Nessuna firma richiesta/)).toBeInTheDocument()
    })
  })

  it('renders panel with firma in corso and Firma ora for current signer', async () => {
    const { getSignaturesByTarget } = await import('../../../services/signatureService')
    vi.mocked(getSignaturesByTarget).mockResolvedValue([
      {
        id: 'sig-1',
        target_type: 'protocol',
        protocol: 'pid-1',
        format: 'cades',
        status: 'pending_otp',
        requested_by: 'u1',
        requested_by_email: 'req@test.com',
        created_at: new Date().toISOString(),
        sequence_steps: [{ id: 1, order: 0, signer: 'user-1', signer_email: 'me@test.com', role_required: 'any', status: 'pending' }],
        current_signer: { id: 'user-1', email: 'me@test.com' },
      } as any,
    ])
    render(
      <SignaturePanel
        targetType="protocol"
        targetId="pid-1"
        canRequestSignature={true}
        currentUserId="user-1"
      />
    )
    await waitFor(() => {
      expect(screen.getByText('Firma ora')).toBeInTheDocument()
    })
  })

  it('shows Richiedi firma when canRequestSignature', async () => {
    render(
      <SignaturePanel
        targetType="protocol"
        targetId="pid-1"
        canRequestSignature={true}
        currentUserId="user-1"
      />
    )
    await waitFor(() => {
      expect(screen.getByText('Richiedi firma')).toBeInTheDocument()
    })
  })

  it('does not show Richiedi firma when canRequestSignature is false', async () => {
    render(
      <SignaturePanel
        targetType="protocol"
        targetId="pid-1"
        canRequestSignature={false}
        currentUserId="user-1"
      />
    )
    await waitFor(() => {
      expect(screen.queryByText('Richiedi firma')).not.toBeInTheDocument()
    })
  })
})
