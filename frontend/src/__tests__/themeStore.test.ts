import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act } from '@testing-library/react'
import { useThemeStore } from '../store/themeStore'

describe('themeStore', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {})
    document.documentElement.classList.remove('dark')
  })

  it('setMode dark updates state and class', () => {
    act(() => {
      useThemeStore.getState().setMode('dark')
    })
    expect(useThemeStore.getState().mode).toBe('dark')
    expect(useThemeStore.getState().effectiveTheme).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('setMode system uses matchMedia result', () => {
    act(() => {
      useThemeStore.getState().setMode('system')
    })
    expect(['light', 'dark']).toContain(useThemeStore.getState().effectiveTheme)
  })

  it('setMode light removes dark class', () => {
    act(() => {
      useThemeStore.getState().setMode('dark')
    })
    act(() => {
      useThemeStore.getState().setMode('light')
    })
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})
