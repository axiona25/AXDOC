import { create } from 'zustand'

/** Mantenuto per compatibilità con import esistenti; l'app è solo tema chiaro. */
export type ThemeMode = 'light' | 'dark' | 'system'

interface ThemeStore {
  mode: ThemeMode
  effectiveTheme: 'light' | 'dark'
  setMode: (mode: ThemeMode) => void
}

function ensureLightDocument() {
  if (typeof document === 'undefined') return
  document.documentElement.classList.remove('dark')
}

if (typeof window !== 'undefined') {
  try {
    localStorage.removeItem('axdoc-theme')
  } catch {
    /* ignore */
  }
  ensureLightDocument()
}

export const useThemeStore = create<ThemeStore>((set) => ({
  mode: 'light',
  effectiveTheme: 'light',
  setMode: () => {
    ensureLightDocument()
    try {
      localStorage.removeItem('axdoc-theme')
    } catch {
      /* ignore */
    }
    set({ mode: 'light', effectiveTheme: 'light' })
  },
}))
