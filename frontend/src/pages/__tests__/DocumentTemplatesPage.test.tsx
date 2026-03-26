import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { DocumentTemplatesPage } from '../DocumentTemplatesPage'

vi.mock('../../services/templateService', () => ({
  getTemplates: vi.fn().mockResolvedValue({ results: [] }),
  deleteTemplate: vi.fn(),
  updateTemplate: vi.fn(),
}))

vi.mock('../../components/documents/TemplateFormModal', () => ({
  TemplateFormModal: () => null,
}))

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({ user: { id: '1', role: 'ADMIN' } }),
  ),
}))

describe('DocumentTemplatesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows nuovo template button', async () => {
    render(
      <MemoryRouter>
        <DocumentTemplatesPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Nuovo template/i })).toBeInTheDocument()
    })
  })

  it('renders template documenti heading', async () => {
    render(
      <MemoryRouter>
        <DocumentTemplatesPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Template documenti/i })).toBeInTheDocument()
    })
  })
})
