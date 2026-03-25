import { create } from 'zustand'

interface NotificationRealtimeState {
  unreadCount: number
  wsConnected: boolean
  setUnreadCount: (n: number) => void
  setWsConnected: (connected: boolean) => void
}

export const useNotificationRealtimeStore = create<NotificationRealtimeState>((set) => ({
  unreadCount: 0,
  wsConnected: false,
  setUnreadCount: (n) => set({ unreadCount: n }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
}))
