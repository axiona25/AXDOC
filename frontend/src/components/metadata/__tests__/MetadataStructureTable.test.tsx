import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MetadataStructureTable } from '../MetadataStructureTable'

const structures = [
  {
    id: '1',
    name: 'Alpha',
    field_count: 3,
    document_count: 5,
    is_active: true,
    fields: [],
  },
] as never

describe('MetadataStructureTable', () => {
  it('renders empty tbody when no structures', () => {
    render(
      <MetadataStructureTable structures={[]} onEdit={vi.fn()} onPreview={vi.fn()} onDelete={vi.fn()} />,
    )
    expect(screen.getByRole('columnheader', { name: /^Nome$/i })).toBeInTheDocument()
  })

  it('renders table headers and row data', () => {
    render(
      <MetadataStructureTable
        structures={structures}
        onEdit={vi.fn()}
        onPreview={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByRole('columnheader', { name: /^Nome$/i })).toBeInTheDocument()
    expect(screen.getByText('Alpha')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Anteprima$/i })).toBeInTheDocument()
  })
})
