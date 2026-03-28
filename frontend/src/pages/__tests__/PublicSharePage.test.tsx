import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { PublicSharePage } from '../PublicSharePage'

vi.mock('../../services/sharingService', () => ({
  getPublicShare: vi.fn(),
  verifySharePassword: vi.fn(),
  downloadSharedFile: vi.fn(),
}))

import * as sharingService from '../../services/sharingService'

describe('PublicSharePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading then shared document when valid', async () => {
    vi.mocked(sharingService.getPublicShare).mockResolvedValue({
      shared_by: { name: 'Alice', email: 'a@test.com' },
      document: {
        title: 'Doc 1',
        description: 'Hi',
        current_version: 1,
        status: 'APPROVED',
      },
      can_download: true,
      expires_at: null,
    } as never)

    render(
      <MemoryRouter initialEntries={['/share/tok']}>
        <Routes>
          <Route path="/share/:token" element={<PublicSharePage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText(/Caricamento/i)).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Doc 1' })).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /Scarica documento/i })).toBeInTheDocument()
  })

  it('shows not found when API returns 404', async () => {
    vi.mocked(sharingService.getPublicShare).mockRejectedValue({
      response: { status: 404 },
    })

    render(
      <MemoryRouter initialEntries={['/share/missing']}>
        <Routes>
          <Route path="/share/:token" element={<PublicSharePage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/Link non trovato/i)).toBeInTheDocument()
    })
  })

  it('shows expired message when API returns 410', async () => {
    vi.mocked(sharingService.getPublicShare).mockRejectedValue({
      response: { status: 410 },
    })

    render(
      <MemoryRouter initialEntries={['/share/exp']}>
        <Routes>
          <Route path="/share/:token" element={<PublicSharePage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/Questo link non è più valido/i)).toBeInTheDocument()
    })
  })

  it('shows password form when API requires password', async () => {
    vi.mocked(sharingService.getPublicShare).mockRejectedValue({
      response: { status: 401, data: { requires_password: true } },
    })

    render(
      <MemoryRouter initialEntries={['/share/tok']}>
        <Routes>
          <Route path="/share/:token" element={<PublicSharePage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Accesso protetto da password/i })).toBeInTheDocument()
    })
    expect(screen.getByPlaceholderText(/Password/i)).toBeInTheDocument()
  })
})
