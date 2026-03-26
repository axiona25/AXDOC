import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { Breadcrumb } from '../Breadcrumb'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="*" element={<Breadcrumb />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Breadcrumb', () => {
  it('shows Home first for nested path', () => {
    renderAt('/documents')
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Documenti')).toBeInTheDocument()
  })

  it('dashboard root shows Dashboard', () => {
    renderAt('/dashboard')
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })
})
