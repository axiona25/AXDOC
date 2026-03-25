import { useState, useEffect, useCallback, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getMailAccounts,
  getMailMessages,
  getMailMessage,
  sendMail,
  markUnread,
  toggleStar,
  fetchMailNow,
  linkToProtocol,
  unlinkFromProtocol,
} from '../services/mailService'
import type {
  MailAccount,
  MailMessageItem,
  MailMessageDetail,
  SendMailPayload,
} from '../services/mailService'

type View = 'inbox' | 'sent' | 'starred' | 'all'

export function MailPage() {
  const queryClient = useQueryClient()
  const [selectedAccountId, setSelectedAccountId] = useState<string | ''>('')
  const [view, setView] = useState<View>('inbox')
  const [typeFilter, setTypeFilter] = useState<'all' | 'email' | 'pec'>('all')
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null)
  const [composeOpen, setComposeOpen] = useState(false)
  const [replyTo, setReplyTo] = useState<MailMessageDetail | null>(null)
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)

  const handleSearchChange = (value: string) => {
    setSearchInput(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => setSearchQuery(value), 400)
  }

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  const { data: accounts = [] } = useQuery({
    queryKey: ['mail-accounts'],
    queryFn: getMailAccounts,
  })

  const filteredAccountIds = typeFilter === 'all'
    ? (selectedAccountId ? [selectedAccountId] : [])
    : accounts.filter((a) => a.account_type === typeFilter).map((a) => a.id)

  const messagesParams = {
    ...(typeFilter !== 'all' && filteredAccountIds.length === 1 && { account: filteredAccountIds[0] }),
    ...(typeFilter === 'all' && selectedAccountId && { account: selectedAccountId }),
    ...(view === 'inbox' && { direction: 'in' as const, folder: 'INBOX' }),
    ...(view === 'sent' && { direction: 'out' as const }),
    ...(searchQuery && { search: searchQuery }),
  }

  const { data: messagesData, isLoading: messagesLoading, refetch: refetchMessages } = useQuery({
    queryKey: ['mail-messages', messagesParams],
    queryFn: () => getMailMessages(messagesParams),
  })

  const filteredMessages = (() => {
    let msgs = messagesData?.results ?? []
    // Filtra per tipo account se il backend non lo supporta nativamente
    if (typeFilter !== 'all' && !selectedAccountId) {
      const typeAccountIds = new Set(accounts.filter((a) => a.account_type === typeFilter).map((a) => a.id))
      msgs = msgs.filter((m) => typeAccountIds.has(m.account))
    }
    if (view === 'starred') msgs = msgs.filter((m) => m.is_starred)
    return msgs
  })()

  const [messageDetail, setMessageDetail] = useState<MailMessageDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const loadDetail = useCallback(
    async (id: string) => {
      setDetailLoading(true)
      try {
        const detail = await getMailMessage(id)
        setMessageDetail(detail)
        refetchMessages()
      } catch {
        setMessageDetail(null)
      } finally {
        setDetailLoading(false)
      }
    },
    [refetchMessages]
  )

  useEffect(() => {
    if (selectedMessageId) loadDetail(selectedMessageId)
    else setMessageDetail(null)
  }, [selectedMessageId, loadDetail])

  useEffect(() => {
    if (accounts.length > 0 && !selectedAccountId) {
      const def = accounts.find((a) => a.is_default) || accounts[0]
      setSelectedAccountId(def.id)
    }
  }, [accounts, selectedAccountId])

  const totalUnread = accounts
    .filter((a) => typeFilter === 'all' || a.account_type === typeFilter)
    .reduce((sum, a) => sum + a.unread_count, 0)

  const handleFetchNow = async () => {
    if (!selectedAccountId) return
    const result = await fetchMailNow(selectedAccountId)
    alert(`Scaricate ${result.fetched} nuove email`)
    queryClient.invalidateQueries({ queryKey: ['mail-accounts'] })
    refetchMessages()
  }

  const handleToggleStar = async (msg: MailMessageItem) => {
    await toggleStar(msg.id)
    refetchMessages()
    if (messageDetail?.id === msg.id) loadDetail(msg.id)
  }

  const handleMarkUnread = async (msg: MailMessageItem) => {
    await markUnread(msg.id)
    refetchMessages()
    setSelectedMessageId(null)
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden rounded-lg border border-slate-200 bg-white shadow dark:border-slate-700 dark:bg-slate-800">
      {/* Sidebar */}
      <div className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-slate-50">
        <div className="border-b border-slate-200 p-3">
          <button
            type="button"
            onClick={() => {
              setComposeOpen(true)
              setReplyTo(null)
            }}
            className="w-full rounded bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            ✉ Nuova email
          </button>
        </div>

        {/* Viste */}
        <div className="flex flex-col gap-0.5 p-2">
          {[
            { id: 'inbox' as View, label: 'Posta in arrivo', icon: '📥', badge: totalUnread },
            { id: 'sent' as View, label: 'Posta inviata', icon: '📤' },
            { id: 'starred' as View, label: 'Speciali', icon: '⭐' },
            { id: 'all' as View, label: 'Tutte', icon: '📬' },
          ].map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => {
                setView(v.id)
                setSelectedMessageId(null)
              }}
              className={`flex items-center justify-between rounded px-2 py-1.5 text-sm ${
                view === v.id
                  ? 'bg-indigo-100 font-medium text-indigo-800'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <span>
                {v.icon} {v.label}
              </span>
              {v.badge ? (
                <span className="rounded-full bg-indigo-600 px-1.5 py-0.5 text-xs text-white">{v.badge}</span>
              ) : null}
            </button>
          ))}
        </div>

        {/* Account */}
        <div className="mt-auto border-t border-slate-200 p-2">
          <p className="mb-1 px-2 text-xs font-medium text-slate-500">Account</p>
          {accounts.filter((a) => typeFilter === 'all' || a.account_type === typeFilter).map((acc) => (
            <button
              key={acc.id}
              type="button"
              onClick={() => {
                setSelectedAccountId(acc.id)
                setSelectedMessageId(null)
              }}
              className={`mb-0.5 flex w-full items-center justify-between rounded px-2 py-1.5 text-xs ${
                selectedAccountId === acc.id ? 'bg-slate-200 font-medium' : 'hover:bg-slate-100'
              }`}
            >
              <span className="truncate">
                {acc.account_type === 'pec' ? '🔐' : '📧'} {acc.name}
              </span>
              {acc.unread_count > 0 && (
                <span className="rounded-full bg-red-500 px-1.5 py-0.5 text-xs text-white">{acc.unread_count}</span>
              )}
            </button>
          ))}
          <div className="mt-2 flex gap-1">
            <button
              type="button"
              onClick={handleFetchNow}
              className="flex-1 rounded bg-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-300"
              title="Scarica nuove email"
            >
              🔄 Aggiorna
            </button>
            <button
              type="button"
              onClick={() => setSettingsOpen(true)}
              className="rounded bg-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-300"
              title="Impostazioni account"
            >
              ⚙
            </button>
          </div>
        </div>
      </div>

      {/* Lista messaggi */}
      <div className="flex w-80 shrink-0 flex-col border-r border-slate-200">
        <div className="border-b border-slate-200 p-2">
          <input
            type="search"
            placeholder="Cerca email..."
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </div>
        <div className="border-b border-slate-200 p-2">
          <div className="flex rounded border border-slate-200 bg-white">
            {[
              { id: 'all' as const, label: 'Tutte' },
              { id: 'email' as const, label: '📧 Email' },
              { id: 'pec' as const, label: '🔐 PEC' },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => {
                  setTypeFilter(t.id)
                  setSelectedMessageId(null)
                }}
                className={`flex-1 px-2 py-1.5 text-xs font-medium transition-colors ${
                  typeFilter === t.id
                    ? 'rounded bg-indigo-600 text-white'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {messagesLoading ? (
            <p className="p-4 text-sm text-slate-500">Caricamento...</p>
          ) : filteredMessages.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">Nessuna email.</p>
          ) : (
            filteredMessages.map((msg) => (
              <button
                key={msg.id}
                type="button"
                onClick={() => setSelectedMessageId(msg.id)}
                className={`flex w-full flex-col border-b border-slate-100 px-3 py-2 text-left transition-colors ${
                  selectedMessageId === msg.id ? 'bg-indigo-50' : 'hover:bg-slate-50'
                } ${msg.status === 'unread' ? 'bg-blue-50/50' : ''}`}
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`truncate text-sm ${
                      msg.status === 'unread' ? 'font-semibold text-slate-800' : 'text-slate-600'
                    }`}
                  >
                    {msg.direction === 'in'
                      ? msg.from_name || msg.from_address
                      : msg.to_addresses[0]?.email || '—'}
                  </span>
                  <div className="flex shrink-0 items-center gap-1">
                    {msg.has_attachments && (
                      <span className="text-xs" title="Allegati">
                        📎
                      </span>
                    )}
                    {msg.is_starred && <span className="text-xs text-amber-500">⭐</span>}
                    {msg.protocol && (
                      <span className="text-xs text-indigo-500" title="Collegato a protocollo">
                        📋
                      </span>
                    )}
                    <span className="text-xs text-slate-400">{msg.account_type === 'pec' ? '🔐' : ''}</span>
                  </div>
                </div>
                <p
                  className={`truncate text-sm ${
                    msg.status === 'unread' ? 'font-medium text-slate-700' : 'text-slate-500'
                  }`}
                >
                  {msg.subject || '(senza oggetto)'}
                </p>
                <div className="mt-0.5 flex items-center justify-between">
                  <span className={`text-xs ${msg.direction === 'in' ? 'text-blue-500' : 'text-amber-500'}`}>
                    {msg.direction === 'in' ? 'Ricevuta' : 'Inviata'}
                  </span>
                  <span className="text-xs text-slate-400">
                    {msg.sent_at ? new Date(msg.sent_at).toLocaleDateString('it-IT') : ''}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Dettaglio / Composizione */}
      <div className="flex flex-1 flex-col">
        {composeOpen ? (
          <ComposePanel
            accounts={accounts}
            defaultAccountId={selectedAccountId}
            replyTo={replyTo}
            onClose={() => {
              setComposeOpen(false)
              setReplyTo(null)
            }}
            onSent={() => {
              setComposeOpen(false)
              setReplyTo(null)
              refetchMessages()
            }}
          />
        ) : messageDetail ? (
          <MessageDetailPanel
            message={messageDetail}
            loading={detailLoading}
            onReply={() => {
              setReplyTo(messageDetail)
              setComposeOpen(true)
            }}
            onToggleStar={() => handleToggleStar(messageDetail)}
            onMarkUnread={() => handleMarkUnread(messageDetail)}
            onClose={() => setSelectedMessageId(null)}
            onRefresh={() => loadDetail(messageDetail.id)}
          />
        ) : (
          <div className="flex flex-1 items-center justify-center text-slate-400">
            <div className="text-center">
              <span className="text-4xl">📧</span>
              <p className="mt-2 text-sm">Seleziona un'email o componi un nuovo messaggio</p>
            </div>
          </div>
        )}
      </div>

      {/* Settings Modal */}
      {settingsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold">Impostazioni Account Email</h2>
            <p className="mb-4 text-sm text-slate-500">
              La configurazione degli account email è disponibile nella sezione Impostazioni dell'applicazione.
            </p>
            <button
              type="button"
              onClick={() => setSettingsOpen(false)}
              className="rounded bg-slate-200 px-4 py-2 text-sm"
            >
              Chiudi
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Compose Panel ─────────────────────────────────
function ComposePanel({
  accounts,
  defaultAccountId,
  replyTo,
  onClose,
  onSent,
}: {
  accounts: MailAccount[]
  defaultAccountId: string
  replyTo: MailMessageDetail | null
  onClose: () => void
  onSent: () => void
}) {
  const [accountId, setAccountId] = useState(defaultAccountId)
  const [to, setTo] = useState(replyTo ? replyTo.from_address : '')
  const [cc, setCc] = useState('')
  const [subject, setSubject] = useState(replyTo ? `Re: ${replyTo.subject}` : '')
  const [body, setBody] = useState(replyTo ? `\n\n--- Messaggio originale ---\n${replyTo.body_text}` : '')
  const [files, setFiles] = useState<File[]>([])
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  const handleSend = async () => {
    if (!to.trim() || !accountId) return
    setSending(true)
    setError('')
    try {
      const payload: SendMailPayload = {
        account_id: accountId,
        to: to
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
        subject,
        body_text: body,
        ...(cc && { cc: cc.split(',').map((c) => c.trim()).filter(Boolean) }),
        ...(replyTo && { reply_to_message_id: replyTo.id }),
      }
      await sendMail(payload, files.length > 0 ? files : undefined)
      onSent()
    } catch (e) {
      setError("Errore durante l'invio.")
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2">
        <h2 className="text-sm font-semibold text-slate-700">{replyTo ? 'Rispondi' : 'Nuovo messaggio'}</h2>
        <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
          ✕
        </button>
      </div>
      <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-4">
        {error && <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        <div className="flex items-center gap-2">
          <label className="w-16 text-sm text-slate-500">Da:</label>
          <select
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm"
          >
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.account_type === 'pec' ? '🔐 ' : ''}
                {a.name} ({a.email_address})
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="w-16 text-sm text-slate-500">A:</label>
          <input
            type="text"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            placeholder="destinatario@email.it"
            className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="w-16 text-sm text-slate-500">Cc:</label>
          <input
            type="text"
            value={cc}
            onChange={(e) => setCc(e.target.value)}
            placeholder="cc@email.it"
            className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="w-16 text-sm text-slate-500">Oggetto:</label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm"
          />
        </div>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={12}
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
          placeholder="Scrivi il tuo messaggio..."
        />
        <div className="flex items-center gap-2">
          <input
            type="file"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
            className="text-sm"
          />
          {files.length > 0 && <span className="text-xs text-slate-500">{files.length} file</span>}
        </div>
      </div>
      <div className="flex justify-end gap-2 border-t border-slate-200 px-4 py-2">
        <button
          type="button"
          onClick={onClose}
          className="rounded bg-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-300"
        >
          Annulla
        </button>
        <button
          type="button"
          onClick={handleSend}
          disabled={sending || !to.trim()}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {sending ? 'Invio...' : '📤 Invia'}
        </button>
      </div>
    </div>
  )
}

// ─── Message Detail Panel ─────────────────────────
function MessageDetailPanel({
  message,
  loading,
  onReply,
  onToggleStar,
  onMarkUnread,
  onClose,
  onRefresh,
}: {
  message: MailMessageDetail
  loading: boolean
  onReply: () => void
  onToggleStar: () => void
  onMarkUnread: () => void
  onClose: () => void
  onRefresh: () => void
}) {
  const [linkProtocolId, setLinkProtocolId] = useState('')

  const handleLinkProtocol = async () => {
    if (!linkProtocolId.trim()) return
    try {
      await linkToProtocol(message.id, linkProtocolId.trim())
      setLinkProtocolId('')
      onRefresh()
    } catch {
      alert('Protocollo non trovato.')
    }
  }

  const handleUnlinkProtocol = async () => {
    await unlinkFromProtocol(message.id)
    onRefresh()
  }

  if (loading)
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-slate-500">Caricamento...</p>
      </div>
    )

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-slate-200 px-4 py-3">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">{message.subject || '(senza oggetto)'}</h2>
          <div className="flex gap-1">
            <button
              type="button"
              onClick={onReply}
              className="rounded bg-indigo-600 px-3 py-1 text-sm text-white hover:bg-indigo-700"
            >
              ↩ Rispondi
            </button>
            <button
              type="button"
              onClick={onToggleStar}
              className="rounded bg-slate-100 px-2 py-1 text-sm hover:bg-slate-200"
            >
              {message.is_starred ? '⭐' : '☆'}
            </button>
            <button
              type="button"
              onClick={onMarkUnread}
              className="rounded bg-slate-100 px-2 py-1 text-sm hover:bg-slate-200"
              title="Segna come non letto"
            >
              ✉
            </button>
            <button type="button" onClick={onClose} className="rounded bg-slate-100 px-2 py-1 text-sm hover:bg-slate-200">
              ✕
            </button>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-600">
          <span>
            <strong>Da:</strong> {message.from_name || message.from_address} &lt;{message.from_address}&gt;
          </span>
          <span>
            <strong>A:</strong> {message.to_addresses.map((a) => a.email).join(', ')}
          </span>
          {message.cc_addresses.length > 0 && (
            <span>
              <strong>Cc:</strong> {message.cc_addresses.map((a) => a.email).join(', ')}
            </span>
          )}
          <span className="text-xs text-slate-400">
            {message.sent_at ? new Date(message.sent_at).toLocaleString('it-IT') : ''}
          </span>
          <span
            className={`rounded px-2 py-0.5 text-xs font-medium ${
              message.account_type === 'pec' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'
            }`}
          >
            {message.account_type === 'pec' ? '🔐 PEC' : '📧 Email'}
          </span>
        </div>
        {/* Collegamento protocollo */}
        <div className="mt-2 flex items-center gap-2">
          {message.protocol ? (
            <div className="flex items-center gap-2 text-sm">
              <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-800">📋 Collegata a protocollo</span>
              <button
                type="button"
                onClick={handleUnlinkProtocol}
                className="text-xs text-red-500 hover:underline"
              >
                Scollega
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={linkProtocolId}
                onChange={(e) => setLinkProtocolId(e.target.value)}
                placeholder="ID protocollo..."
                className="w-48 rounded border border-slate-300 px-2 py-1 text-xs"
              />
              <button
                type="button"
                onClick={handleLinkProtocol}
                className="rounded bg-slate-200 px-2 py-1 text-xs hover:bg-slate-300"
              >
                Collega
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4">
        {message.body_html ? (
          <div className="prose prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: message.body_html }} />
        ) : (
          <pre className="whitespace-pre-wrap text-sm text-slate-700">{message.body_text}</pre>
        )}
      </div>

      {/* Allegati */}
      {message.attachments.length > 0 && (
        <div className="border-t border-slate-200 px-4 py-2">
          <p className="mb-1 text-xs font-medium text-slate-500">Allegati ({message.attachments.length})</p>
          <div className="flex flex-wrap gap-2">
            {message.attachments.map((att) => (
              <a
                key={att.id}
                href={att.url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50"
              >
                📎 {att.filename}{' '}
                <span className="text-slate-400">({(att.size / 1024).toFixed(0)} KB)</span>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
