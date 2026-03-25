import { useCallback, useEffect, useRef, useState } from 'react'
import { Monitor, Moon, Sun } from 'lucide-react'
import { useThemeStore, type ThemeMode } from '../../store/themeStore'

const MODES: ThemeMode[] = ['light', 'dark', 'system']

const LABELS: Record<ThemeMode, string> = {
  light: 'Tema chiaro',
  dark: 'Tema scuro',
  system: 'Tema di sistema',
}

export function ThemeToggle() {
  const mode = useThemeStore((s) => s.mode)
  const setMode = useThemeStore((s) => s.setMode)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const cycle = useCallback(() => {
    const i = MODES.indexOf(mode)
    setMode(MODES[(i + 1) % MODES.length])
  }, [mode, setMode])

  const Icon = mode === 'dark' ? Moon : mode === 'light' ? Sun : Monitor

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        onDoubleClick={(e) => {
          e.preventDefault()
          cycle()
        }}
        title={`Tema: ${LABELS[mode]} (doppio click per ciclare)`}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="rounded p-2 text-slate-600 transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
      >
        <Icon className="h-5 w-5" aria-hidden />
        <span className="sr-only">{LABELS[mode]}</span>
      </button>
      {open && (
        <ul
          role="listbox"
          className="absolute right-0 z-50 mt-1 min-w-[11rem] rounded-lg border border-slate-200 bg-white py-1 text-sm shadow-lg dark:border-slate-600 dark:bg-slate-800"
        >
          {MODES.map((m) => (
            <li key={m} role="option" aria-selected={mode === m}>
              <button
                type="button"
                onClick={() => {
                  setMode(m)
                  setOpen(false)
                }}
                className={`flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-700 ${
                  mode === m ? 'font-semibold text-indigo-600 dark:text-indigo-400' : 'text-slate-700 dark:text-slate-200'
                }`}
              >
                {m === 'light' && <Sun className="h-4 w-4" />}
                {m === 'dark' && <Moon className="h-4 w-4" />}
                {m === 'system' && <Monitor className="h-4 w-4" />}
                {LABELS[m]}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
