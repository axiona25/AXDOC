import { useEffect } from 'react'

/**
 * Escape chiude la modal; usare con useFocusTrap sul pannello.
 */
export function useModalEscape(isOpen: boolean, onClose: () => void) {
  useEffect(() => {
    if (!isOpen) return
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [isOpen, onClose])
}
