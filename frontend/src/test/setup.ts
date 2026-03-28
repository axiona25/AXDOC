import '@testing-library/jest-dom'
import { vi } from 'vitest'

Element.prototype.scrollIntoView = vi.fn()

const lsStore: Record<string, string> = {}
const localStorageMock = {
  getItem: (key: string) => (key in lsStore ? lsStore[key] : null),
  setItem: (key: string, value: string) => {
    lsStore[key] = value
  },
  removeItem: (key: string) => {
    delete lsStore[key]
  },
  clear: () => {
    for (const k of Object.keys(lsStore)) delete lsStore[k]
  },
  key: (i: number) => Object.keys(lsStore)[i] ?? null,
  get length() {
    return Object.keys(lsStore).length
  },
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock, writable: true })

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})
