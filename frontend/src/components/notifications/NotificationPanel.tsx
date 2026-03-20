import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getNotifications, markRead, getNotification } from '../../services/notificationService'
import type { NotificationItem } from '../../services/notificationService'
import { NotificationItemView } from './NotificationItem'

interface NotificationPanelProps {
  onClose: () => void
  onMarkAllRead?: () => void
}

export function NotificationPanel({ onClose, onMarkAllRead }: NotificationPanelProps) {
  const [tab, setTab] = useState<'unread' | 'all'>('unread')
  const [list, setList] = useState<NotificationItem[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const load = () => {
    setLoading(true)
    const params = tab === 'unread' ? { unread: 'true' } : {}
    getNotifications(params)
      .then((res) => setList(res.results || (Array.isArray(res) ? res : [])))
      .catch(() => setList([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [tab])

  const handleMarkAllRead = async () => {
    await markRead({ all: true })
    onMarkAllRead?.()
    load()
  }

  const handleClick = async (n: NotificationItem) => {
    if (!n.is_read) {
      await getNotification(n.id)
      markRead({ ids: [n.id] }).catch(() => {})
    }
    onClose()
    if (n.link_url) {
      const path = n.link_url.startsWith('/') ? n.link_url : `/${n.link_url}`
      navigate(path)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onClick={onClose}>
      <div
        className="w-full max-w-md bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-lg font-semibold text-slate-800">Notifiche</h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleMarkAllRead}
              className="rounded bg-slate-100 px-2 py-1 text-sm text-slate-700 hover:bg-slate-200"
            >
              Segna tutte come lette
            </button>
            <button type="button" onClick={onClose} className="rounded p-1 text-slate-500 hover:bg-slate-100">
              ✕
            </button>
          </div>
        </div>
        <div className="flex border-b border-slate-200">
          <button
            type="button"
            onClick={() => setTab('unread')}
            className={`flex-1 px-4 py-2 text-sm font-medium ${tab === 'unread' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-slate-600'}`}
          >
            Non lette
          </button>
          <button
            type="button"
            onClick={() => setTab('all')}
            className={`flex-1 px-4 py-2 text-sm font-medium ${tab === 'all' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-slate-600'}`}
          >
            Tutte
          </button>
        </div>
        <div className="max-h-[70vh] overflow-auto">
          {loading ? (
            <p className="p-4 text-sm text-slate-500">Caricamento...</p>
          ) : list.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">Nessuna notifica.</p>
          ) : (
            <ul>
              {list.map((n) => (
                <NotificationItemView
                  key={n.id}
                  notification={n}
                  onClick={() => handleClick(n)}
                />
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
