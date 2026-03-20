import { useState, useEffect } from 'react'
import { getUnreadCount, pollUnreadCount } from '../../services/notificationService'
import { NotificationPanel } from './NotificationPanel'

const POLL_INTERVAL_MS = 30000

export function NotificationBell() {
  const [count, setCount] = useState(0)
  const [panelOpen, setPanelOpen] = useState(false)

  const refresh = () => {
    getUnreadCount().then((r) => setCount(r.count)).catch(() => setCount(0))
  }

  useEffect(() => {
    refresh()
    const id = setInterval(() => {
      pollUnreadCount().then((r) => setCount(r.unread_count)).catch(() => {})
    }, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [])

  return (
    <>
      <button
        type="button"
        onClick={() => setPanelOpen(true)}
        className="relative rounded p-2 text-slate-600 hover:bg-slate-100"
        aria-label="Notifiche"
      >
        <span className="text-lg">🔔</span>
        {count > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-500 px-1 text-xs text-white">
            {count > 99 ? '99+' : count}
          </span>
        )}
      </button>
      {panelOpen && (
        <NotificationPanel
          onClose={() => setPanelOpen(false)}
          onMarkAllRead={refresh}
        />
      )}
    </>
  )
}
