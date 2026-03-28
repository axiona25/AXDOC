import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ImportUsersModal } from '../ImportUsersModal'
import * as userService from '../../../services/userService'

vi.mock('../../../services/userService', () => ({
  downloadImportTemplate: vi.fn().mockResolvedValue(new Blob()),
  importPreview: vi.fn(),
  importUsers: vi.fn(),
}))

describe('ImportUsersModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders upload area', () => {
    render(<ImportUsersModal isOpen onClose={() => {}} onSuccess={() => {}} />)
    expect(
      screen.getByText(/Scarica il template e carica un file CSV o Excel/i),
    ).toBeInTheDocument()
  })

  it('shows Scarica CSV and Scarica Excel', () => {
    render(<ImportUsersModal isOpen onClose={() => {}} onSuccess={() => {}} />)
    expect(screen.getByRole('button', { name: /Scarica CSV/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Scarica Excel/i })).toBeInTheDocument()
  })

  it('accepts csv file selection', async () => {
    const user = userEvent.setup()
    render(<ImportUsersModal isOpen onClose={() => {}} onSuccess={() => {}} />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['a,b'], 'test.csv', { type: 'text/csv' })
    await user.upload(input, file)
    expect(screen.getByText(/test\.csv/i)).toBeInTheDocument()
  })

  it('download template calls downloadImportTemplate', async () => {
    const user = userEvent.setup()
    render(<ImportUsersModal isOpen onClose={() => {}} onSuccess={() => {}} />)
    await user.click(screen.getByRole('button', { name: /Scarica CSV/i }))
    await waitFor(() => {
      expect(userService.downloadImportTemplate).toHaveBeenCalledWith('csv')
    })
  })
})
