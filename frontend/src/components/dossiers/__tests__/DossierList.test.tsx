import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { DossierList } from '../DossierList'

const d = {
  id: 'd1',
  title: 'Fascicolo uno',
  identifier: '2025/U1/0001',
  status: 'active',
  organizational_unit_name: 'UO',
} as never

describe('DossierList', () => {
  it('renders tabs', () => {
    render(
      <MemoryRouter>
        <DossierList
          dossiers={[]}
          activeTab="mine"
          onTabChange={() => {}}
          onOpen={vi.fn()}
        />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: /I miei fascicoli/i })).toBeInTheDocument()
  })

  it('shows dossier row when data present', () => {
    render(
      <MemoryRouter>
        <DossierList
          dossiers={[d]}
          activeTab="all"
          onTabChange={() => {}}
          onOpen={vi.fn()}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText('Fascicolo uno')).toBeInTheDocument()
  })
})
