import { api } from './api'

export interface NotificationItem {
  id: string
  notification_type: string
  title: string
  body: string
  is_read: boolean
  read_at: string | null
  created_at: string
  link_url: string
  metadata: Record<string, unknown>
}

export interface NotificationsResponse {
  results: NotificationItem[]
  count?: number
  next?: string | null
  previous?: string | null
}

export function getNotifications(params?: { unread?: string; read?: string; page?: number }): Promise<NotificationsResponse> {
  return api.get<NotificationsResponse>('/api/notifications/', { params }).then((r) => r.data)
}

export function getNotification(id: string): Promise<NotificationItem> {
  return api.get<NotificationItem>(`/api/notifications/${id}/`).then((r) => r.data)
}

export function markRead(payload: { ids?: string[]; all?: boolean }): Promise<{ marked: number }> {
  return api.post<{ marked: number }>('/api/notifications/mark_read/', payload).then((r) => r.data)
}

export function getUnreadCount(): Promise<{ count: number }> {
  return api.get<{ count: number }>('/api/notifications/unread_count/').then((r) => r.data)
}

export function pollUnreadCount(): Promise<{ unread_count: number }> {
  return api.get<{ unread_count: number }>('/api/notifications/poll/').then((r) => r.data)
}
