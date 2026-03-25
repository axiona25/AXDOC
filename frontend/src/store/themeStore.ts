import { create } from 'zustand'

export type ThemeMode = 'light' | 'dark' | 'system'

interface ThemeStore {
  mode: ThemeMode
  effectiveTheme: 'light' | 'dark'
  setMode: (mode: ThemeMode) => void
}

function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return 'light'
  try {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

function getStoredMode(): ThemeMode {
  if (typeof window !== 'undefined') {
    const v = localStorage.getItem('axdoc-theme') as ThemeMode | null
    if (v === 'light' || v === 'dark' || v === 'system') return v
  }
  return 'system'
}

function resolveTheme(mode: ThemeMode): 'light' | 'dark' {
  if (mode === 'system') return getSystemTheme()
  return mode
}

function applyTheme(theme: 'light' | 'dark') {
  const root = document.documentElement
  if (theme === 'dark') root.classList.add('dark')
  else root.classList.remove('dark')
}

const initialMode = getStoredMode()
const initialEffective = resolveTheme(initialMode)
applyTheme(initialEffective)

export const useThemeStore = create<ThemeStore>((set) => ({
  mode: initialMode,
  effectiveTheme: initialEffective,
  setMode: (mode) => {
    localStorage.setItem('axdoc-theme', mode)
    const effective = resolveTheme(mode)
    applyTheme(effective)
    set({ mode, effectiveTheme: effective })
  },
}))

if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
  try {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      const state = useThemeStore.getState()
      if (state.mode === 'system') {
        const effective = getSystemTheme()
        applyTheme(effective)
        useThemeStore.setState({ effectiveTheme: effective })
      }
    })
  } catch {
    /* ignore */
  }
}
