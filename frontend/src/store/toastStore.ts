import { create } from 'zustand'

export interface ToastNotification {
  id: string
  title: string
  message: string
  notification_type: string
  link_url: string
  timestamp: number
}

const MAX_TOASTS = 3

interface ToastStore {
  toasts: ToastNotification[]
  addToast: (notification: Omit<ToastNotification, 'id' | 'timestamp'>) => void
  removeToast: (id: string) => void
  clearAll: () => void
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (notification) => {
    const newToast: ToastNotification = {
      ...notification,
      id: `toast_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
      timestamp: Date.now(),
    }
    set((state) => {
      const updated = [...state.toasts, newToast]
      return { toasts: updated.slice(-MAX_TOASTS) }
    })
  },
  removeToast: (id) =>
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
  clearAll: () => set({ toasts: [] }),
}))

export const OPEN_NOTIFICATIONS_EVENT = 'axdoc:open-notifications'

export function requestOpenNotificationsPanel(): void {
  document.dispatchEvent(new CustomEvent(OPEN_NOTIFICATIONS_EVENT))
}
