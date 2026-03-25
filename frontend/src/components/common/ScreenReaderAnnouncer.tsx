let announceTimeout: ReturnType<typeof setTimeout> | undefined

export function announce(message: string, priority: 'polite' | 'assertive' = 'polite') {
  const el = document.getElementById('sr-announcer')
  if (!el) return
  el.setAttribute('aria-live', priority)
  el.textContent = ''
  if (announceTimeout) clearTimeout(announceTimeout)
  announceTimeout = setTimeout(() => {
    el.textContent = message
  }, 100)
}

export function ScreenReaderAnnouncer() {
  return (
    <div
      id="sr-announcer"
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    />
  )
}
