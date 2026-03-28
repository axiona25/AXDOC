import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { TenantSelector } from '../TenantSelector'

vi.mock('../../../services/tenantService', () => ({
  getTenantCurrent: vi.fn().mockResolvedValue({ id: 't1', name: 'Tenant Demo' }),
  getTenants: vi.fn().mockResolvedValue([]),
}))

vi.mock('../../../store/authStore', () => ({
  useAuthStore: vi.fn((sel: (s: unknown) => unknown) =>
    sel({
      user: { id: 'u1', is_superuser: false },
    }),
  ),
}))

describe('TenantSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows current tenant name when loaded', async () => {
    render(<TenantSelector />)
    await waitFor(() => {
      expect(document.body.textContent).toContain('Tenant Demo')
    })
  })
})
