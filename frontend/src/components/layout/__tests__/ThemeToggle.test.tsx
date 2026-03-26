import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeToggle } from '../ThemeToggle'
import { useThemeStore } from '../../../store/themeStore'

describe('ThemeToggle', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {})
    useThemeStore.setState({ mode: 'light', effectiveTheme: 'light' })
  })

  it('opens menu and sets dark mode', async () => {
    const user = userEvent.setup()
    render(<ThemeToggle />)
    await user.click(screen.getByRole('button', { name: /Tema chiaro|Tema scuro|Tema di sistema/i }))
    await user.click(screen.getByRole('button', { name: /Tema scuro/i }))
    expect(useThemeStore.getState().mode).toBe('dark')
  })
})
