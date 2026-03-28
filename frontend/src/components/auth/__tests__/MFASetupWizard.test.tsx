import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MFASetupWizard } from '../MFASetupWizard'

vi.mock('../../../services/authService', () => ({
  initMFASetup: vi.fn().mockResolvedValue({
    secret: 's',
    qr_url: 'data:image/png;base64,xx',
    otpauth_url: 'otpauth://totp/test',
  }),
  confirmMFASetup: vi.fn(),
}))

describe('MFASetupWizard', () => {
  it('shows intro then QR after Continua', async () => {
    const user = userEvent.setup()
    render(<MFASetupWizard open onClose={() => {}} onSuccess={vi.fn()} />)
    expect(screen.getByRole('heading', { name: /Configura autenticazione a due fattori/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /^Continua$/i }))
    await waitFor(() => {
      expect(screen.getByText(/Scansiona questo QR code/i)).toBeInTheDocument()
    })
  })
})
