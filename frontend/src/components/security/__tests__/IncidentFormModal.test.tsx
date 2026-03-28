import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { IncidentFormModal } from '../IncidentFormModal'

describe('IncidentFormModal', () => {
  it('renders edit title when initial incident provided', () => {
    render(
      <IncidentFormModal
        open
        initial={
          {
            id: 'i1',
            title: 'T',
            description: 'D',
            severity: 'low',
            status: 'open',
            category: 'other',
            affected_systems: '',
            affected_users_count: 0,
            data_compromised: false,
            containment_actions: '',
            remediation_actions: '',
            reported_to_authority: false,
            authority_report_date: null,
            authority_reference: '',
            reported_by: null,
            reported_by_email: null,
            assigned_to: null,
            assigned_to_email: null,
            detected_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            resolved_at: null,
          } as never
        }
        onClose={vi.fn()}
        onSave={vi.fn().mockResolvedValue(undefined)}
      />,
    )
    expect(screen.getByRole('heading', { name: /Modifica incidente/i })).toBeInTheDocument()
  })

  it('renders new incident title and required fields', () => {
    render(
      <IncidentFormModal open onClose={vi.fn()} onSave={vi.fn().mockResolvedValue(undefined)} />,
    )
    expect(screen.getByRole('heading', { name: /Nuovo incidente/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/Titolo \*/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Descrizione \*/i)).toBeInTheDocument()
  })
})
