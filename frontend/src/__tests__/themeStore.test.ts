import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act } from '@testing-library/react'
import { useThemeStore } from '../store/themeStore'

describe('themeStore', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {})
    document.documentElement.classList.remove('dark')
  })

  it('setMode non applica mai la classe dark al documento', () => {
    act(() => {
      useThemeStore.getState().setMode('dark')
    })
    expect(useThemeStore.getState().mode).toBe('light')
    expect(useThemeStore.getState().effectiveTheme).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('setMode system mantiene tema effettivo chiaro', () => {
    act(() => {
      useThemeStore.getState().setMode('system')
    })
    expect(useThemeStore.getState().effectiveTheme).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('setMode dopo dark rimuove eventuale classe dark', () => {
    document.documentElement.classList.add('dark')
    act(() => {
      useThemeStore.getState().setMode('light')
    })
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})
