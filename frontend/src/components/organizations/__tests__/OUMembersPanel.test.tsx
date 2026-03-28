import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OUMembersPanel } from '../OUMembersPanel'

vi.mock('../../../services/organizationService', () => ({
  getOUMembers: vi.fn().mockResolvedValue([]),
  addMember: vi.fn(),
  removeMember: vi.fn(),
}))

vi.mock('../../../services/userService', () => ({
  getUsers: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../../services/groupService', () => ({
  getGroups: vi.fn().mockResolvedValue({ results: [] }),
  createGroup: vi.fn(),
  deleteGroup: vi.fn(),
}))

const ou = { id: 'ou1', name: 'UO Test', code: 'T', parent: null } as never

describe('OUMembersPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows members section for OU', async () => {
    render(
      <MemoryRouter>
        <OUMembersPanel ou={ou} onExport={vi.fn()} onRefresh={vi.fn()} />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Membri — UO Test/i })).toBeInTheDocument()
    })
  })
})
