import { useEffect, useRef } from 'react'

const FOCUSABLE =
  'button:not([disabled]), [href]:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

function getFocusable(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => el.getAttribute('aria-hidden') !== 'true' && !el.hasAttribute('disabled'),
  )
}

/**
 * Intrappola il focus quando attivo; al cleanup ripristina il focus precedente.
 * Escape va gestito dal chiamante (es. chiusura modal).
 */
export function useFocusTrap(isActive: boolean) {
  const containerRef = useRef<HTMLDivElement>(null)
  const previousFocus = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!isActive) return

    previousFocus.current = document.activeElement as HTMLElement | null
    const container = containerRef.current
    if (!container) return

    const focusable = getFocusable(container)
    if (focusable.length > 0) {
      focusable[0].focus()
    } else {
      container.setAttribute('tabindex', '-1')
      container.focus()
    }

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab' || focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault()
          last.focus()
        }
      } else if (document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    container.addEventListener('keydown', onKeyDown)
    return () => {
      container.removeEventListener('keydown', onKeyDown)
      container.removeAttribute('tabindex')
      previousFocus.current?.focus?.()
    }
  }, [isActive])

  return containerRef
}
