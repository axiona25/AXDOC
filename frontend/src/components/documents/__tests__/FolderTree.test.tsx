import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FolderTree } from '../FolderTree'

const folders = [
  { id: 'f1', name: 'Cartella A', parent: null as string | null, tenant: 't' },
]

describe('FolderTree', () => {
  it('renders root and folder', () => {
    const onSelect = vi.fn()
    render(
      <FolderTree folders={folders as never} selectedId={null} onSelect={onSelect} />,
    )
    expect(screen.getByRole('button', { name: /Root/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Cartella A/i })).toBeInTheDocument()
  })

  it('click root calls onSelect(null)', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(
      <FolderTree folders={[]} selectedId="f1" onSelect={onSelect} />,
    )
    await user.click(screen.getByRole('button', { name: /Root/i }))
    expect(onSelect).toHaveBeenCalledWith(null)
  })
})
