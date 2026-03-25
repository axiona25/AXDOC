import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getProtocol,
  archiveProtocol,
  downloadProtocolDocument,
  addProtocolAttachment,
} from '../services/protocolService'
import type { ProtocolDetailItem } from '../services/protocolService'
import { getDocuments } from '../services/documentService'
import type { DocumentItem } from '../services/documentService'
import { getMailMessages } from '../services/mailService'
import type { MailMessageItem } from '../services/mailService'
import { DocumentViewer } from '../components/viewer/DocumentViewer'
import { SignaturePanel } from '../components/signatures/SignaturePanel'
import { useAuthStore } from '../store/authStore'
import { useBreadcrumbTitle } from '../components/layout/BreadcrumbContext'

type TabId = 'documents' | 'dossiers' | 'emails' | 'signature' | 'audit'

export function ProtocolDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [protocol, setProtocol] = useState<ProtocolDetailItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<TabId>('documents')
  const [addDocId, setAddDocId] = useState('')
  const [availableDocs, setAvailableDocs] = useState<DocumentItem[]>([])
  const [protocolEmails, setProtocolEmails] = useState<MailMessageItem[]>([])
  const [emailsLoading, setEmailsLoading] = useState(false)
  const [archiving, setArchiving] = useState(false)
  const [viewerDocId, setViewerDocId] = useState<string | null>(null)
  const user = useAuthStore((s) => s.user)
  const { setEntityTitle } = useBreadcrumbTitle()

  const load = useCallback(() => {
    if (!id) return
    setLoading(true)
    getProtocol(id)
      .then(setProtocol)
      .catch(() => setProtocol(null))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!protocol) {
      setEntityTitle(null)
      return
    }
    const t =
      protocol.protocol_id || protocol.protocol_display || protocol.subject || null
    setEntityTitle(t)
    return () => setEntityTitle(null)
  }, [protocol, setEntityTitle])

  useEffect(() => {
    getDocuments({ page: 1 })
      .then((r) => setAvailableDocs(r.results || []))
      .catch(() => setAvailableDocs([]))
  }, [])

  useEffect(() => {
    if (tab === 'emails' && id) {
      setEmailsLoading(true)
      getMailMessages({ protocol: id })
        .then((r) => setProtocolEmails(r.results || []))
        .catch(() => setProtocolEmails([]))
        .finally(() => setEmailsLoading(false))
    }
  }, [tab, id])

  const handleArchive = async () => {
    if (!protocol || !confirm('Archiviare questo protocollo?')) return
    setArchiving(true)
    try {
      await archiveProtocol(protocol.id)
      load()
    } catch {
      alert('Errore durante l\'archiviazione')
    } finally {
      setArchiving(false)
    }
  }

  const handleDownload = () => {
    if (!protocol) return
    if (!protocol.document && !protocol.document_file) {
      alert('Nessun documento allegato a questo protocollo.')
      return
    }
    downloadProtocolDocument(protocol.id).catch(() =>
      alert('Download non disponibile. Il documento potrebbe non avere un file fisico.')
    )
  }

  const handleStampedDocument = () => {
    if (!protocol) return
    if (!protocol.document && !protocol.document_file) {
      alert('Nessun documento da timbrare.')
      return
    }
    import('../services/api').then(({ api }) => {
      api
        .get(`/api/protocols/${protocol.id}/stamped_document/`, { responseType: 'blob' })
        .then((res) => {
          const blob = res.data as Blob
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `${protocol.protocol_id?.replace(/\//g, '_') || protocol.id}_timbrato.pdf`
          a.click()
          URL.revokeObjectURL(url)
        })
        .catch(() => alert('Errore nel generare il documento timbrato.'))
    })
  }

  const handleAddAttachment = async () => {
    if (!protocol || !addDocId.trim()) return
    try {
      await addProtocolAttachment(protocol.id, addDocId.trim())
      setAddDocId('')
      load()
    } catch (e) {
      const err = e as { response?: { data?: { document_id?: string; detail?: string } } }
      alert(err?.response?.data?.document_id || err?.response?.data?.detail || 'Errore')
    }
  }

  if (loading || !protocol) {
    return (
      <div className="p-6">
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Caricamento...</p>
        ) : (
          <p className="text-slate-500 dark:text-slate-400">Protocollo non trovato.</p>
        )}
      </div>
    )
  }

  const tabs: { id: TabId; label: string }[] = [
    { id: 'documents', label: 'Documenti allegati' },
    { id: 'dossiers', label: 'Fascicoli collegati' },
    { id: 'emails', label: 'Email / PEC' },
    { id: 'signature', label: 'Documenti firmati' },
    { id: 'audit', label: 'Log' },
  ]

  return (
    <div className="flex flex-col rounded-lg border border-slate-200 bg-white shadow dark:border-slate-700 dark:bg-slate-800">
      <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
        <div className="flex items-center justify-between">
          <div>
            <button
              type="button"
              onClick={() => navigate('/protocols')}
              className="text-sm text-indigo-600 hover:underline dark:text-indigo-400"
            >
              ← Protocolli
            </button>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Segnatura AGID
            </p>
            <h1 className="mt-0.5 text-xl font-semibold text-slate-800 dark:text-slate-100">
              {(protocol.segnatura ?? protocol.protocol_id) || protocol.protocol_display || protocol.id}
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-300">{protocol.subject}</p>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <span>{protocol.direction === 'in' ? 'In entrata' : 'In uscita'}</span>
              <span>•</span>
              <span>{protocol.organizational_unit_name || '—'}</span>
              <span>•</span>
              <span>
                {protocol.registered_at
                  ? new Date(protocol.registered_at).toLocaleString('it-IT')
                  : '—'}
              </span>
              <span
                className={`rounded px-2 py-0.5 font-medium ${
                  protocol.status === 'archived'
                    ? 'bg-slate-200 text-slate-700 dark:bg-slate-600 dark:text-slate-100'
                    : 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
                }`}
              >
                {protocol.status === 'archived' ? 'Archiviato' : 'Attivo'}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleDownload}
              disabled={!protocol.document && !protocol.document_file}
              className={`rounded px-3 py-1.5 text-sm font-medium ${
                protocol.document || protocol.document_file
                  ? 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-100 dark:hover:bg-slate-600'
                  : 'cursor-not-allowed bg-slate-50 text-slate-300 dark:bg-slate-800 dark:text-slate-600'
              }`}
              title={
                protocol.document || protocol.document_file
                  ? 'Scarica documento'
                  : 'Nessun documento allegato'
              }
            >
              Scarica documento
            </button>
            <button
              type="button"
              onClick={handleStampedDocument}
              disabled={!protocol.document && !protocol.document_file}
              className={`rounded px-3 py-1.5 text-sm font-medium ${
                protocol.document || protocol.document_file
                  ? 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-100 dark:hover:bg-slate-600'
                  : 'cursor-not-allowed bg-slate-50 text-slate-300 dark:bg-slate-800 dark:text-slate-600'
              }`}
              title={
                protocol.document || protocol.document_file
                  ? 'Scarica con timbro AGID'
                  : 'Nessun documento da timbrare'
              }
            >
              Documento timbrato
            </button>
            {protocol.status !== 'archived' && (
              <button
                type="button"
                onClick={handleArchive}
                disabled={archiving}
                className="rounded bg-amber-100 px-3 py-1.5 text-sm font-medium text-amber-800 hover:bg-amber-200 disabled:opacity-50 dark:bg-amber-900/40 dark:text-amber-200 dark:hover:bg-amber-900/60"
              >
                {archiving ? 'Archiviazione...' : 'Archivia'}
              </button>
            )}
          </div>
        </div>
      </div>

      <nav className="flex gap-2 border-b border-slate-200 px-4 dark:border-slate-700">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`border-b-2 px-3 py-2 text-sm font-medium ${
              tab === t.id
                ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                : 'border-transparent text-slate-600 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="min-h-[200px] p-4">
        {tab === 'documents' && (
          <div>
            <p className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Documento principale</p>
            {protocol.document ? (
              <div className="mb-4 flex items-center justify-between rounded border border-slate-200 px-3 py-2 dark:border-slate-600">
                <span className="text-sm text-slate-900 dark:text-slate-100">
                  {protocol.document_title || protocol.document}
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setViewerDocId(protocol.document!)}
                    className="text-sm text-indigo-600 hover:underline dark:text-indigo-400"
                  >
                    Visualizza
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate(`/documents?doc=${protocol.document}`)}
                    className="text-sm text-slate-600 hover:underline dark:text-slate-300"
                  >
                    Apri in Documenti
                  </button>
                </div>
              </div>
            ) : (
              <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">Nessun documento principale.</p>
            )}

            <p className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Allegati</p>
            {protocol.status !== 'archived' && (
              <div className="mb-3 flex gap-2">
                <input
                  type="text"
                  placeholder="ID documento da allegare"
                  value={addDocId}
                  onChange={(e) => setAddDocId(e.target.value)}
                  className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
                />
                <button
                  type="button"
                  onClick={handleAddAttachment}
                  className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 dark:hover:bg-indigo-500"
                >
                  Aggiungi
                </button>
              </div>
            )}
            <ul className="space-y-2">
              {(protocol.attachment_ids || []).map((docId) => (
                <li
                  key={docId}
                  className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm dark:border-slate-600"
                >
                  <span className="text-slate-700 dark:text-slate-200">
                    {availableDocs.find((d) => d.id === docId)?.title || docId}
                  </span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setViewerDocId(docId)}
                      className="text-indigo-600 hover:underline dark:text-indigo-400"
                    >
                      Visualizza
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate(`/documents?doc=${docId}`)}
                      className="text-slate-600 hover:underline dark:text-slate-300"
                    >
                      Apri in Documenti
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            {(!protocol.attachment_ids || protocol.attachment_ids.length === 0) && (
              <p className="text-sm text-slate-500 dark:text-slate-400">Nessun allegato.</p>
            )}
          </div>
        )}

        {tab === 'dossiers' && (
          <div>
            {protocol.dossier_ids && protocol.dossier_ids.length > 0 ? (
              <ul className="space-y-2">
                {protocol.dossier_ids.map((dId) => (
                  <li
                    key={dId}
                    className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm dark:border-slate-600"
                  >
                    <span className="font-mono text-slate-600 dark:text-slate-300">{dId}</span>
                    <button
                      type="button"
                      onClick={() => navigate(`/dossiers/${dId}`)}
                      className="text-indigo-600 hover:underline dark:text-indigo-400"
                    >
                      Apri fascicolo
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500 dark:text-slate-400">Nessun fascicolo collegato a questo protocollo.</p>
            )}
          </div>
        )}

        {tab === 'emails' && (
          <div>
            {emailsLoading ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">Caricamento...</p>
            ) : protocolEmails.length > 0 ? (
              <div className="space-y-2">
                {protocolEmails.map((email) => (
                  <div
                    key={email.id}
                    className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 dark:border-slate-600"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                            email.direction === 'in'
                              ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200'
                              : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200'
                          }`}
                        >
                          {email.direction === 'in' ? 'IN' : 'OUT'}
                        </span>
                        <span
                          className={`rounded px-1.5 py-0.5 text-xs ${
                            email.account_type === 'pec'
                              ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200'
                              : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
                          }`}
                        >
                          {email.account_type === 'pec' ? '🔐 PEC' : '📧 Email'}
                        </span>
                        <span className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">
                          {email.subject || '(senza oggetto)'}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                        {email.direction === 'in' ? `Da: ${email.from_name || email.from_address}` : `A: ${email.to_addresses[0]?.email || '—'}`}
                        {' · '}
                        {email.sent_at ? new Date(email.sent_at).toLocaleString('it-IT') : ''}
                        {email.has_attachments && ' · 📎'}
                      </p>
                    </div>
                    <a href="/mail" className="shrink-0 text-sm text-indigo-600 hover:underline dark:text-indigo-400">
                      Apri in Posta
                    </a>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <span className="mb-2 text-3xl">📧</span>
                <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Nessuna email collegata</p>
                <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                  Puoi collegare email a questo protocollo dalla sezione Posta.
                </p>
              </div>
            )}
          </div>
        )}

        {tab === 'signature' && id && user && (
          <SignaturePanel
            targetType="protocol"
            targetId={id}
            canRequestSignature={user.role === 'ADMIN' || user.role === 'APPROVER'}
            currentUserId={user.id}
          />
        )}

        {tab === 'audit' && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <span className="mb-2 text-3xl">📋</span>
            <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Log attività</p>
            <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
              Il registro delle modifiche e degli accessi sarà disponibile prossimamente.
            </p>
          </div>
        )}
      </div>

      {viewerDocId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="flex h-full max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl dark:border-slate-600 dark:bg-slate-800">
            <DocumentViewer documentId={viewerDocId} onClose={() => setViewerDocId(null)} showHeader />
          </div>
        </div>
      )}
    </div>
  )
}
