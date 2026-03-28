import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { LDAPStatusCard } from '../LDAPStatusCard'

describe('LDAPStatusCard', () => {
  it('renders heading', () => {
    render(<LDAPStatusCard />)
    expect(screen.getByRole('heading', { name: /Stato LDAP/i })).toBeInTheDocument()
  })
})
