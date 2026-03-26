import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { PrivacyConsentPage } from '../PrivacyConsentPage'

vi.mock('../../services/privacyService', () => ({
  getMyConsents: vi.fn().mockResolvedValue([]),
  exportMyData: vi.fn(),
  grantConsent: vi.fn(),
}))

vi.mock('../../components/common/ScreenReaderAnnouncer', () => ({
  announce: vi.fn(),
}))

describe('PrivacyConsentPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows esporta dati button', async () => {
    render(
      <MemoryRouter>
        <PrivacyConsentPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Esporta i miei dati/i })).toBeInTheDocument()
    })
  })

  it('renders privacy e consensi', async () => {
    render(
      <MemoryRouter>
        <PrivacyConsentPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: /Privacy e consensi/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText(/Caricamento/i)).not.toBeInTheDocument()
    })
  })
})
