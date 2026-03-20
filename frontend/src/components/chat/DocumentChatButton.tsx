import { useState } from 'react'
import { getDocumentChat } from '../../services/chatService'
import type { ChatRoomItem } from '../../services/chatService'
import { ChatWindow } from './ChatWindow'

interface DocumentChatButtonProps {
  documentId: string
  documentTitle?: string
}

export function DocumentChatButton({ documentId, documentTitle }: DocumentChatButtonProps) {
  const [open, setOpen] = useState(false)
  const [room, setRoom] = useState<ChatRoomItem | null>(null)
  const [loading, setLoading] = useState(false)

  const handleOpen = () => {
    setOpen(true)
    if (!room) {
      setLoading(true)
      getDocumentChat(documentId)
        .then(setRoom)
        .catch(() => setRoom(null))
        .finally(() => setLoading(false))
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={handleOpen}
        className="rounded bg-slate-100 px-2 py-1 text-sm text-slate-700 hover:bg-slate-200"
      >
        💬 Chat
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/20" onClick={() => setOpen(false)}>
          <div className="h-full w-full max-w-md bg-white shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2">
                <h3 className="font-medium text-slate-800">Chat: {documentTitle || 'Documento'}</h3>
                <button type="button" onClick={() => setOpen(false)} className="rounded p-1 hover:bg-slate-100">
                  ✕
                </button>
              </div>
              {loading ? (
                <p className="p-4 text-sm text-slate-500">Caricamento...</p>
              ) : room ? (
                <ChatWindow
                  room={room}
                  onBack={() => setOpen(false)}
                />
              ) : (
                <p className="p-4 text-sm text-slate-500">Impossibile aprire la chat.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
