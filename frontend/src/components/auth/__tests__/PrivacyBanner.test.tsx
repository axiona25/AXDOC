import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { PrivacyBanner } from '../PrivacyBanner'
import { useAuthStore } from '../../../store/authStore'

vi.mock('../../../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

vi.mock('../../../services/privacyService', () => ({
  getMyConsents: vi.fn().mockResolvedValue([]),
  grantConsent: vi.fn(),
}))

describe('PrivacyBanner', () => {
  beforeEach(() => {
    vi.mocked(useAuthStore).mockImplementation((sel) =>
      sel({
        user: { id: '1', email: 'a@test.com' } as never,
      } as never),
    )
  })

  it('renders checkboxes and accept', async () => {
    render(<PrivacyBanner />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Accetta/i })).toBeInTheDocument()
    })
  })
})
