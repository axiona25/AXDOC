import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { WorkflowBuilderPage } from '../WorkflowBuilderPage'

vi.mock('../../services/workflowService', () => ({
  getWorkflowTemplates: vi.fn().mockResolvedValue({ results: [] }),
  getWorkflowTemplate: vi.fn(),
  createWorkflowTemplate: vi.fn(),
  deleteWorkflowTemplate: vi.fn(),
  publishWorkflow: vi.fn(),
  unpublishWorkflow: vi.fn(),
  createWorkflowStep: vi.fn(),
  updateWorkflowStep: vi.fn(),
  deleteWorkflowStep: vi.fn(),
}))

vi.mock('../../services/userService', () => ({
  getUsers: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../services/organizationService', () => ({
  getOrganizationalUnits: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({ user: { id: '1', role: 'ADMIN' } }),
  ),
}))

describe('WorkflowBuilderPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows nuovo workflow button', async () => {
    render(
      <MemoryRouter initialEntries={['/workflows']}>
        <WorkflowBuilderPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Nuovo workflow/i })).toBeInTheDocument()
    })
  })

  it('renders workflow builder heading', async () => {
    render(
      <MemoryRouter initialEntries={['/workflows']}>
        <WorkflowBuilderPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Workflow Builder/i })).toBeInTheDocument()
    })
  })
})
