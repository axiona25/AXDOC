import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { P7MViewer } from '../P7MViewer'

vi.mock('../../../services/signatureService', () => ({
  verifyP7M: vi.fn(),
  extractP7MContent: vi.fn(),
}))

describe('P7MViewer', () => {
  it('renders verify and extract actions', () => {
    const file = new File(['x'], 'test.p7m', { type: 'application/pkcs7-mime' })
    render(<P7MViewer file={file} fileName="test.p7m" />)
    expect(screen.getByRole('button', { name: /Verifica firma/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Estrai documento/i })).toBeInTheDocument()
  })

  it('shows placeholder when no verify result', () => {
    render(<P7MViewer file={new File([], 'a.p7m')} />)
    expect(screen.getByText(/File con firma digitale CAdES/i)).toBeInTheDocument()
  })
})
