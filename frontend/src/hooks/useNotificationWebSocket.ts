import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { getAccessToken } from '../services/api'

export interface NotificationWS {
  id: string
  title: string
  message: string
  body: string
  verb: string
  notification_type: string
  is_read: boolean
  link_url: string
  created_at: string | null
  read_at?: string | null
  metadata?: Record<string, unknown>
}

export interface UseNotificationWebSocketOptions {
  onNotification?: (notification: NotificationWS) => void
  onUnreadCount?: (count: number) => void
  onConnectionChange?: (connected: boolean) => void
  enabled?: boolean
}

function getWebSocketBaseUrl(): string {
  if (import.meta.env.DEV) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}`
  }
  const api = import.meta.env.VITE_API_URL || ''
  if (api) {
    try {
      const u = new URL(api)
      const wsProto = u.protocol === 'https:' ? 'wss:' : 'ws:'
      return `${wsProto}//${u.host}`
    } catch {
      /* ignore */
    }
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

export function useNotificationWebSocket(options: UseNotificationWebSocketOptions = {}) {
  const { onNotification, onUnreadCount, onConnectionChange, enabled = true } = options
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const isLoading = useAuthStore((s) => s.isLoading)

  const onNotificationRef = useRef(onNotification)
  const onUnreadCountRef = useRef(onUnreadCount)
  const onConnectionChangeRef = useRef(onConnectionChange)
  onNotificationRef.current = onNotification
  onUnreadCountRef.current = onUnreadCount
  onConnectionChangeRef.current = onConnectionChange

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout>>()
  const [isConnected, setIsConnected] = useState(false)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10
  const intentionalClose = useRef(false)

  const effectiveEnabled = enabled && !isLoading && isAuthenticated && !!getAccessToken()

  const connect = useCallback(() => {
    const token = getAccessToken()
    if (!token || !effectiveEnabled) {
      return
    }

    intentionalClose.current = false
    const wsUrl = `${getWebSocketBaseUrl()}/ws/notifications/?token=${encodeURIComponent(token)}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      reconnectAttempts.current = 0
      onConnectionChangeRef.current?.(true)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as {
          type?: string
          notification?: NotificationWS
          count?: number
        }
        if (data.type === 'new_notification' && data.notification && onNotificationRef.current) {
          onNotificationRef.current(data.notification)
        }
        if (
          (data.type === 'unread_count' || data.type === 'unread_count_update') &&
          typeof data.count === 'number' &&
          onUnreadCountRef.current
        ) {
          onUnreadCountRef.current(data.count)
        }
      } catch {
        /* ignore parse errors */
      }
    }

    ws.onclose = (event) => {
      setIsConnected(false)
      wsRef.current = null
      onConnectionChangeRef.current?.(false)

      if (intentionalClose.current || event.code === 4001 || event.code === 1000) {
        return
      }

      if (reconnectAttempts.current < maxReconnectAttempts && effectiveEnabled) {
        const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000)
        reconnectAttempts.current += 1
        reconnectTimeout.current = setTimeout(connect, delay)
      }
    }

    ws.onerror = () => {
      /* onclose gestisce reconnect */
    }
  }, [effectiveEnabled])

  const markRead = useCallback((notificationId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'mark_read', notification_id: notificationId }))
    }
  }, [])

  const markAllRead = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'mark_all_read' }))
    }
  }, [])

  useEffect(() => {
    if (!effectiveEnabled) {
      intentionalClose.current = true
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current)
      if (wsRef.current) {
        wsRef.current.close(1000)
        wsRef.current = null
      }
      setIsConnected(false)
      onConnectionChangeRef.current?.(false)
      return
    }

    connect()
    return () => {
      intentionalClose.current = true
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current)
      if (wsRef.current) {
        wsRef.current.close(1000)
        wsRef.current = null
      }
    }
  }, [connect, effectiveEnabled])

  return { isConnected, markRead, markAllRead }
}
