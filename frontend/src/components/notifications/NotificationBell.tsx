import { useState, useEffect, useCallback } from 'react'
import { getUnreadCount, pollUnreadCount } from '../../services/notificationService'
import { NotificationPanel } from './NotificationPanel'
import { useAuthStore } from '../../store/authStore'
import { OPEN_NOTIFICATIONS_EVENT } from '../../store/toastStore'
import { useNotificationRealtimeStore } from '../../store/notificationRealtimeStore'
import { useNotificationWs } from './NotificationWsContext'

const FALLBACK_POLL_MS = 30000
const WS_FALLBACK_DELAY_MS = 5000

export function NotificationBell() {
  const [panelOpen, setPanelOpen] = useState(false)
  const [useFallbackPolling, setUseFallbackPolling] = useState(false)

  const count = useNotificationRealtimeStore((s) => s.unreadCount)
  const setUnreadCount = useNotificationRealtimeStore((s) => s.setUnreadCount)

  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const isLoading = useAuthStore((s) => s.isLoading)
  const { isConnected, markRead, markAllRead } = useNotificationWs()

  const refresh = useCallback(() => {
    getUnreadCount().then((r) => setUnreadCount(r.count)).catch(() => setUnreadCount(0))
  }, [setUnreadCount])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    const open = () => setPanelOpen(true)
    document.addEventListener(OPEN_NOTIFICATIONS_EVENT, open)
    return () => document.removeEventListener(OPEN_NOTIFICATIONS_EVENT, open)
  }, [])

  useEffect(() => {
    if (!isAuthenticated) {
      setUseFallbackPolling(false)
    }
  }, [isAuthenticated])

  useEffect(() => {
    const timer = setTimeout(() => {
      if (!isAuthenticated || isLoading) return
      if (!isConnected) setUseFallbackPolling(true)
    }, WS_FALLBACK_DELAY_MS)
    return () => clearTimeout(timer)
  }, [isConnected, isAuthenticated, isLoading])

  useEffect(() => {
    if (isConnected) setUseFallbackPolling(false)
  }, [isConnected])

  useEffect(() => {
    if (!useFallbackPolling) return
    const id = setInterval(() => {
      pollUnreadCount().then((r) => setUnreadCount(r.unread_count)).catch(() => {})
    }, FALLBACK_POLL_MS)
    return () => clearInterval(id)
  }, [useFallbackPolling, setUnreadCount])

  return (
    <>
      <button
        type="button"
        onClick={() => setPanelOpen(true)}
        className="relative rounded p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
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
          wsConnected={isConnected}
          onWsMarkRead={markRead}
          onWsMarkAllRead={markAllRead}
        />
      )}
    </>
  )
}
