import { useState, useEffect, useRef } from 'react'
import { getRoomMessages, sendMessage } from '../../services/chatService'
import type { ChatRoomItem, ChatMessageItem } from '../../services/chatService'
import { useAuthStore } from '../../store/authStore'

interface ChatWindowProps {
  room: ChatRoomItem
  onBack: () => void
  onMessage?: () => void
}

export function ChatWindow({ room, onBack, onMessage }: ChatWindowProps) {
  const user = useAuthStore((s) => s.user)
  const [messages, setMessages] = useState<ChatMessageItem[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const isOwnMessage = (m: ChatMessageItem) => user?.email && m.sender_email === user.email

  useEffect(() => {
    getRoomMessages(room.id).then((r) => setMessages(r.results || [])).catch(() => setMessages([]))
  }, [room.id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending) return
    setSending(true)
    try {
      const msg = await sendMessage(room.id, text)
      setMessages((prev) => [...prev, msg])
      setInput('')
      onMessage?.()
    } catch {
      // ignore
    } finally {
      setSending(false)
    }
  }

  const title = room.name || room.members?.map((m) => m.user_email).filter(Boolean).join(', ') || 'Chat'

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex items-center gap-2 border-b border-slate-200 px-3 py-2">
        <button type="button" onClick={onBack} className="rounded p-1 text-slate-600 hover:bg-slate-100">
          ←
        </button>
        <h3 className="flex-1 truncate text-sm font-medium text-slate-800">{title}</h3>
      </div>
      <div className="flex-1 overflow-auto p-3">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`mb-2 rounded-lg px-3 py-2 text-sm ${isOwnMessage(m) ? 'ml-8 bg-indigo-100 text-right' : 'bg-slate-100 text-left'}`}
          >
            {!isOwnMessage(m) && m.sender_email && <div className="text-xs text-slate-500">{m.sender_email}</div>}
            <div>{m.content || '(allegato)'}</div>
            <div className="mt-0.5 text-xs text-slate-400">
              {new Date(m.sent_at).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={handleSend} className="border-t border-slate-200 p-2">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Scrivi un messaggio..."
            className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
            disabled={sending}
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Invia
          </button>
        </div>
      </form>
    </div>
  )
}
