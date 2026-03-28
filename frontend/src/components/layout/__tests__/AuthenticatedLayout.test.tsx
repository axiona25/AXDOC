import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthenticatedLayout } from '../AuthenticatedLayout'

vi.mock('../../auth/PrivacyBanner', () => ({
  PrivacyBanner: () => null,
}))
vi.mock('../TenantSelector', () => ({
  TenantSelector: () => <span data-testid="tenant-selector">Tenant</span>,
}))
vi.mock('../ThemeToggle', () => ({
  ThemeToggle: () => null,
}))
vi.mock('../Breadcrumb', () => ({
  Breadcrumb: () => <nav aria-label="breadcrumb">Nav</nav>,
}))

describe('AuthenticatedLayout', () => {
  it('renders tenant selector slot', () => {
    render(
      <MemoryRouter>
        <AuthenticatedLayout>
          <span>inner</span>
        </AuthenticatedLayout>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('tenant-selector')).toBeInTheDocument()
  })

  it('renders banner header and main with main-content id', () => {
    render(
      <MemoryRouter>
        <AuthenticatedLayout>
          <p>Page body</p>
        </AuthenticatedLayout>
      </MemoryRouter>,
    )
    expect(screen.getByRole('banner')).toBeInTheDocument()
    const main = document.getElementById('main-content')
    expect(main).toBeTruthy()
    expect(main).toHaveAttribute('role', 'main')
    expect(screen.getByText('Page body')).toBeInTheDocument()
  })
})
