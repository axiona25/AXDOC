import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { UserTable } from '../UserTable'

const noop = () => {}

describe('UserTable', () => {
  it('renders table headers and user row', () => {
    render(
      <UserTable
        data={{
          results: [
            {
              id: 'u1',
              email: 'a@test.com',
              first_name: 'Ada',
              last_name: 'Test',
              role: 'ADMIN',
              user_type: 'internal',
              is_active: true,
              is_guest: false,
              date_joined: '2026-01-01T00:00:00Z',
              organizational_units: [],
            } as never,
          ],
          count: 1,
          next: null,
          previous: null,
        }}
        isLoading={false}
        onEdit={vi.fn()}
        roleFilter=""
        onRoleFilterChange={noop}
        userTypeFilter=""
        onUserTypeFilterChange={noop}
        activeFilter=""
        onActiveFilterChange={noop}
        search=""
        onSearchChange={noop}
      />,
    )
    expect(screen.getByRole('columnheader', { name: /^Email$/i })).toBeInTheDocument()
    expect(screen.getByText('a@test.com')).toBeInTheDocument()
    expect(screen.getByText(/Totale: 1 utenti/i)).toBeInTheDocument()
  })

  it('shows loading text when loading', () => {
    render(
      <UserTable
        data={undefined}
        isLoading
        onEdit={vi.fn()}
        roleFilter=""
        onRoleFilterChange={noop}
        userTypeFilter=""
        onUserTypeFilterChange={noop}
        activeFilter=""
        onActiveFilterChange={noop}
        search=""
        onSearchChange={noop}
      />,
    )
    expect(screen.getByText(/Caricamento/i)).toBeInTheDocument()
  })
})
