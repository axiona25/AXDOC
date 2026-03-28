import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SSOButtons } from '../SSOButtons'
import { api } from '../../../services/api'

vi.mock('../../../services/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

describe('SSOButtons', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('google')) return Promise.resolve({ data: { auth_url: 'https://google.test' } })
      if (url.includes('microsoft')) return Promise.resolve({ data: { auth_url: 'https://ms.test' } })
      return Promise.reject(new Error())
    })
  })

  it('renders Google and Microsoft links', async () => {
    render(
      <MemoryRouter>
        <SSOButtons />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(/Accedi con Google/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/Microsoft/i)).toBeInTheDocument()
  })
})
