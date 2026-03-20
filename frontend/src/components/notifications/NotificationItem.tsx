import type { NotificationItem } from '../../services/notificationService'

interface NotificationItemViewProps {
  notification: NotificationItem
  onClick: () => void
}

function formatRelative(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return 'ora'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} min fa`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} ore fa`
  return d.toLocaleDateString('it-IT')
}

export function NotificationItemView({ notification, onClick }: NotificationItemViewProps) {
  const bodyShort = notification.body.length > 120 ? notification.body.slice(0, 120) + '…' : notification.body
  return (
    <li
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      className={`cursor-pointer border-b border-slate-100 px-4 py-3 text-left hover:bg-slate-50 ${!notification.is_read ? 'bg-indigo-50/50' : ''}`}
    >
      <div className="font-medium text-slate-800">{notification.title}</div>
      <div className="mt-0.5 text-sm text-slate-600">{bodyShort}</div>
      <div className="mt-1 text-xs text-slate-400">{formatRelative(notification.created_at)}</div>
    </li>
  )
}
