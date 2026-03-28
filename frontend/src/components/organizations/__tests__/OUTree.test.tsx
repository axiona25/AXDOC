import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { OUTree } from '../OUTree'

const units = [
  {
    id: 'u1',
    name: 'Root OU',
    code: 'ROOT',
    parent: null,
    children: [{ id: 'u2', name: 'Child', code: 'CH', parent: 'u1', children: [] }],
  },
] as never

describe('OUTree', () => {
  it('renders OU tree with root and nested child (default expanded)', () => {
    const onSelect = vi.fn()
    render(
      <OUTree units={units} selectedId={null} onSelect={onSelect} />,
    )
    expect(screen.getByText(/ROOT — Root OU/)).toBeInTheDocument()
    expect(screen.getByText(/CH — Child/)).toBeInTheDocument()
  })
})
