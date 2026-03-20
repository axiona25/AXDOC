import { useState, useEffect } from 'react'
import { getChatRooms, getUnreadCount } from '../../services/chatService'
import type { ChatRoomItem } from '../../services/chatService'
import { ChatWindow } from './ChatWindow'

interface ChatPanelProps {
  open: boolean
  onClose: () => void
}

export function ChatPanel({ open, onClose }: ChatPanelProps) {
  const [rooms, setRooms] = useState<ChatRoomItem[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [selectedRoom, setSelectedRoom] = useState<ChatRoomItem | null>(null)
  const [loading, setLoading] = useState(true)

  const load = () => {
    getChatRooms().then(setRooms).catch(() => setRooms([]))
    getUnreadCount().then((r) => setUnreadCount(r.count)).catch(() => setUnreadCount(0))
  }

  useEffect(() => {
    if (open) load()
  }, [open])

  useEffect(() => {
    setLoading(false)
  }, [rooms])

  if (!open) return null

  return (
    <div className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <h2 className="text-lg font-semibold text-slate-800">
          Chat
          {unreadCount > 0 && (
            <span className="ml-2 rounded-full bg-red-500 px-2 py-0.5 text-xs text-white">
              {unreadCount}
            </span>
          )}
        </h2>
        <button type="button" onClick={onClose} className="rounded p-1 text-slate-500 hover:bg-slate-100">
          ✕
        </button>
      </div>
      {selectedRoom ? (
        <ChatWindow
          room={selectedRoom}
          onBack={() => setSelectedRoom(null)}
          onMessage={() => load()}
        />
      ) : (
        <div className="flex-1 overflow-auto p-2">
          {loading ? (
            <p className="text-sm text-slate-500">Caricamento...</p>
          ) : rooms.length === 0 ? (
            <p className="text-sm text-slate-500">Nessuna chat. Avvia una chat da un documento o con un utente.</p>
          ) : (
            <ul className="space-y-1">
              {rooms.map((room) => (
                <li key={room.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedRoom(room)}
                    className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left hover:bg-slate-50"
                  >
                    <span className="flex-1 truncate font-medium text-slate-800">
                      {room.name || room.members?.map((m) => m.user_email).filter(Boolean).join(', ') || room.id.slice(0, 8)}
                    </span>
                    {room.unread_count > 0 && (
                      <span className="rounded-full bg-indigo-500 px-2 py-0.5 text-xs text-white">
                        {room.unread_count}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
