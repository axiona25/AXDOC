import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { WorkflowTab } from '../WorkflowTab'

vi.mock('../../../services/workflowService', () => ({
  getWorkflowInstances: vi.fn().mockResolvedValue([]),
  getPublishedTemplates: vi.fn().mockResolvedValue([]),
  startWorkflow: vi.fn(),
  performStepAction: vi.fn(),
  cancelWorkflow: vi.fn(),
}))

vi.mock('../../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: { user: { id: string } | null }) => unknown) =>
    sel({ user: { id: 'u1', email: 'a@test.com', role: 'ADMIN' } as never }),
  ),
}))

vi.mock('../../common/ScreenReaderAnnouncer', () => ({
  announce: vi.fn(),
}))

describe('WorkflowTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows empty state when no templates and no instances', async () => {
    render(<WorkflowTab documentId="doc-1" />)
    await waitFor(() => {
      expect(screen.getByText(/Nessun workflow disponibile/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('heading', { name: /Workflow documentale/i })).toBeInTheDocument()
  })
})
