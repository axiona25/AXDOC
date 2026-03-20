import { api } from './api'

export interface ChatRoomItem {
  id: string
  room_type: string
  name: string
  document_id: string | null
  dossier_id: string | null
  protocol_id: string | null
  created_at: string
  last_message: { id: string; content: string; sender_id: string | null; sent_at: string } | null
  unread_count: number
  members: { user_id: string; user_email: string; is_online?: boolean }[]
}

export interface ChatMessageItem {
  id: string
  room: string
  sender_id: string | null
  sender_email: string | null
  message_type: string
  content: string
  file?: string
  file_name?: string
  file_size?: number
  image?: string
  sent_at: string
  edited_at: string | null
  reply_to_id: string | null
}

export function getChatRooms(): Promise<ChatRoomItem[]> {
  return api.get('/api/chat/rooms/').then((r) => (Array.isArray(r.data) ? r.data : (r.data?.results ?? [])) as ChatRoomItem[])
}

export function createDirectChat(userId: string): Promise<ChatRoomItem> {
  return api.post('/api/chat/rooms/direct/', { user_id: userId }).then((r) => r.data)
}

export function getRoomMessages(roomId: string, page = 1): Promise<{ results: ChatMessageItem[]; count: number }> {
  return api.get(`/api/chat/rooms/${roomId}/messages/`, { params: { page } }).then((r) => r.data)
}

export function sendMessage(roomId: string, content: string, replyTo?: string): Promise<ChatMessageItem> {
  return api.post(`/api/chat/rooms/${roomId}/messages/`, { content, reply_to: replyTo }).then((r) => r.data)
}

export function uploadChatFile(roomId: string, file: File): Promise<ChatMessageItem> {
  const form = new FormData()
  form.append('file', file)
  return api.post(`/api/chat/rooms/${roomId}/upload/`, form).then((r) => r.data)
}

export function deleteMessage(messageId: string): Promise<void> {
  return api.delete(`/api/chat/messages/${messageId}/`)
}

export function getUnreadCount(): Promise<{ count: number }> {
  return api.get('/api/chat/rooms/unread_count/').then((r) => r.data)
}

export function getDocumentChat(documentId: string): Promise<ChatRoomItem> {
  return api.post(`/api/documents/${documentId}/chat/`).then((r) => r.data)
}

export function getDossierChat(dossierId: string): Promise<ChatRoomItem> {
  return api.post(`/api/dossiers/${dossierId}/chat/`).then((r) => r.data)
}

export function initiateCall(targetUserId: string): Promise<{ call_id: string; ws_url: string }> {
  return api.post('/api/chat/calls/initiate/', { target_user_id: targetUserId }).then((r) => r.data)
}

export function endCall(callId: string): Promise<{ ok: boolean }> {
  return api.post(`/api/chat/calls/${callId}/end/`).then((r) => r.data)
}

export function getIceServers(): Promise<{ ice_servers: { urls: string }[] }> {
  return api.get('/api/chat/ice_servers/').then((r) => r.data)
}
