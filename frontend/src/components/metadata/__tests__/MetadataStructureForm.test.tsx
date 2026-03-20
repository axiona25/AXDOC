import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MetadataStructureForm } from '../MetadataStructureForm'

describe('MetadataStructureForm', () => {
  it('renders name and description inputs', () => {
    render(
      <MetadataStructureForm
        structure={null}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.getByLabelText(/Nome/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Descrizione/)).toBeInTheDocument()
  })

  it('has add field button', () => {
    render(
      <MetadataStructureForm
        structure={null}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.getByRole('button', { name: /Aggiungi campo/ })).toBeInTheDocument()
  })

  it('adds a field when clicking add', async () => {
    const user = userEvent.setup()
    render(
      <MetadataStructureForm
        structure={null}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    await user.click(screen.getByRole('button', { name: /Aggiungi campo/ }))
    expect(screen.getByPlaceholderText(/Nome tecnico/)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Etichetta/)).toBeInTheDocument()
  })

  it('submit sends structured data', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(
      <MetadataStructureForm
        structure={null}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />
    )
    const nameInput = screen.getByLabelText(/Nome \*/)
    await user.type(nameInput, 'Contratto')
    await user.click(screen.getByRole('button', { name: 'Salva' }))
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Contratto',
        fields: expect.any(Array),
      })
    )
  })
})
