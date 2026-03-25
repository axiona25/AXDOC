import { createContext, useContext, useEffect, useRef, type ReactNode } from 'react'
import { useAuthStore } from '../../store/authStore'
import { useToastStore } from '../../store/toastStore'
import { useNotificationRealtimeStore } from '../../store/notificationRealtimeStore'
import { useNotificationWebSocket } from '../../hooks/useNotificationWebSocket'

export interface NotificationWsContextValue {
  isConnected: boolean
  markRead: (id: string) => void
  markAllRead: () => void
}

const NotificationWsContext = createContext<NotificationWsContextValue | null>(null)

const noopWs: NotificationWsContextValue = {
  isConnected: false,
  markRead: () => {},
  markAllRead: () => {},
}

export function NotificationWsProvider({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const isLoading = useAuthStore((s) => s.isLoading)
  const addToast = useToastStore((s) => s.addToast)
  const clearToasts = useToastStore((s) => s.clearAll)
  const setUnreadCount = useNotificationRealtimeStore((s) => s.setUnreadCount)
  const setWsConnected = useNotificationRealtimeStore((s) => s.setWsConnected)
  const wasAuthed = useRef(false)

  useEffect(() => {
    if (wasAuthed.current && !isAuthenticated) {
      clearToasts()
      setUnreadCount(0)
      setWsConnected(false)
    }
    wasAuthed.current = isAuthenticated
  }, [isAuthenticated, clearToasts, setUnreadCount, setWsConnected])

  const { isConnected, markRead, markAllRead } = useNotificationWebSocket({
    enabled: !isLoading && isAuthenticated,
    onUnreadCount: setUnreadCount,
    onConnectionChange: setWsConnected,
    onNotification: (n) => {
      addToast({
        title: n.title,
        message: n.body || n.message || '',
        notification_type: n.notification_type || '',
        link_url: n.link_url || '',
      })
    },
  })

  const value: NotificationWsContextValue = { isConnected, markRead, markAllRead }

  return (
    <NotificationWsContext.Provider value={value}>{children}</NotificationWsContext.Provider>
  )
}

export function useNotificationWs(): NotificationWsContextValue {
  return useContext(NotificationWsContext) ?? noopWs
}
