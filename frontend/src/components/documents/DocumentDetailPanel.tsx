import { useState, useEffect } from 'react'
import type { DocumentItem, DocumentVersionItem } from '../../services/documentService'
import {
  getDocumentVersions,
  getDocumentAttachments,
  downloadDocument,
  downloadAttachment,
  unlockDocument,
  uploadAttachment,
  deleteAttachment,
  updateDocumentMetadata,
} from '../../services/documentService'
import { getMetadataStructure } from '../../services/metadataService'
import type { MetadataStructure } from '../../types/metadata'
import { DocumentLockBadge } from './DocumentLockBadge'
import { DynamicMetadataForm } from '../metadata/DynamicMetadataForm'
import { ProtocolFormModal } from '../protocols/ProtocolFormModal'
import {
  getDocumentSignatures,
  getDocumentConservation,
  checkConservationStatus,
} from '../../services/signatureService'
import type { SignatureRequestItem, ConservationRequestItem } from '../../types/signatures'
import { getDocumentShares, shareDocument, revokeShare } from '../../services/sharingService'
import type { ShareLinkItem } from '../../services/sharingService'
import { ShareListPanel } from '../sharing/ShareListPanel'
import { ShareModal } from '../sharing/ShareModal'
import { getDocumentActivity } from '../../services/auditService'
import type { AuditLogItem } from '../../services/auditService'
import { ActivityTimeline } from '../audit/ActivityTimeline'
import { DocumentChatButton } from '../chat/DocumentChatButton'
import { useAuthStore } from '../../store/authStore'
import { VersionHistoryModal } from './VersionHistoryModal'

interface DocumentDetailPanelProps {
  document: DocumentItem | null
  onClose: () => void
  onRefresh: () => void
  onNewVersion: (doc: DocumentItem) => void
  /** FASE 19: apre DocumentViewer */
  onVisualize?: () => void
}

export function DocumentDetailPanel({
  document: doc,
  onClose,
  onRefresh,
  onNewVersion,
  onVisualize,
}: DocumentDetailPanelProps) {
  const [tab, setTab] = useState<'info' | 'versions' | 'attachments' | 'metadata' | 'protocols' | 'signatures' | 'conservation' | 'sharing' | 'activity' | 'permissions'>('info')
  const [versions, setVersions] = useState<DocumentVersionItem[]>(doc?.versions ?? [])
  const [attachments, setAttachments] = useState<DocumentItem['attachments']>(doc?.attachments ?? [])
  const [metadataStructure, setMetadataStructure] = useState<MetadataStructure | null>(null)
  const [metadataEdit, setMetadataEdit] = useState(false)
  const [metadataEditValues, setMetadataEditValues] = useState<Record<string, unknown>>({})
  const [metadataSaving, setMetadataSaving] = useState(false)
  const [metadataErrors, setMetadataErrors] = useState<Record<string, string>>({})
  const [versionModalOpen, setVersionModalOpen] = useState(false)
  const [protocolModalOpen, setProtocolModalOpen] = useState(false)
  const [signaturesList, setSignaturesList] = useState<SignatureRequestItem[]>([])
  const [conservationList, setConservationList] = useState<ConservationRequestItem[]>([])
  const [sharesList, setSharesList] = useState<ShareLinkItem[]>([])
  const [shareModalOpen, setShareModalOpen] = useState(false)
  const [activityList, setActivityList] = useState<AuditLogItem[]>([])
  const [unlocking, setUnlocking] = useState(false)
  const [attachFile, setAttachFile] = useState<File | null>(null)
  const [attachDesc, setAttachDesc] = useState('')
  const user = useAuthStore((s) => s.user)
  const isLockedByMe = doc?.locked_by && user && String(doc.locked_by) === String(user.id)

  const metadataStructureId =
    typeof doc?.metadata_structure === 'object' && doc?.metadata_structure !== null
      ? (doc.metadata_structure as { id: string }).id
      : (doc?.metadata_structure as string | undefined)
  const metadataValues = doc?.metadata_values ?? {}

  if (!doc) return null

  const loadAttachments = () => {
    getDocumentAttachments(doc.id).then((list) => {
      setAttachments(list)
      onRefresh()
    })
  }

  const handleUnlock = async () => {
    setUnlocking(true)
    try {
      await unlockDocument(doc.id)
      onRefresh()
    } finally {
      setUnlocking(false)
    }
  }

  const handleDownload = () => {
    const firstVersion = (versions && versions.length > 0) ? versions[0] : null
    const name = firstVersion?.file_name ?? doc.title
    downloadDocument(doc.id, undefined, name)
  }

  const handleUploadAttachment = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!attachFile) return
    try {
      await uploadAttachment(doc.id, attachFile, attachDesc || undefined)
      setAttachFile(null)
      setAttachDesc('')
      loadAttachments()
    } catch (err) {
      console.error(err)
    }
  }

  const handleDeleteAttachment = async (attId: string) => {
    try {
      await deleteAttachment(doc.id, attId)
      loadAttachments()
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    if (tab === 'metadata' && metadataStructureId) {
      getMetadataStructure(metadataStructureId).then(setMetadataStructure)
    } else if (tab !== 'metadata') {
      setMetadataStructure(null)
    }
  }, [tab, metadataStructureId])

  useEffect(() => {
    if (tab === 'signatures' && doc) {
      getDocumentSignatures(doc.id).then(setSignaturesList).catch(() => setSignaturesList([]))
    }
  }, [tab, doc?.id])

  useEffect(() => {
    if (tab === 'conservation' && doc) {
      getDocumentConservation(doc.id).then(setConservationList).catch(() => setConservationList([]))
    }
  }, [tab, doc?.id])

  useEffect(() => {
    if (tab === 'sharing' && doc) {
      getDocumentShares(doc.id).then(setSharesList).catch(() => setSharesList([]))
    }
  }, [tab, doc?.id])

  useEffect(() => {
    if (tab === 'activity' && doc) {
      getDocumentActivity(doc.id).then(setActivityList).catch(() => setActivityList([]))
    }
  }, [tab, doc?.id])

  const loadMetadataStructure = () => {
    if (metadataStructureId) {
      getMetadataStructure(metadataStructureId).then(setMetadataStructure)
    } else {
      setMetadataStructure(null)
    }
  }

  const tabs = [
    { id: 'info' as const, label: 'Info' },
    { id: 'versions' as const, label: 'Versioni' },
    { id: 'attachments' as const, label: 'Allegati' },
    ...(metadataStructureId ? [{ id: 'metadata' as const, label: 'Metadati' }] : []),
    { id: 'protocols' as const, label: 'Protocolli' },
    { id: 'signatures' as const, label: 'Firma' },
    { id: 'conservation' as const, label: 'Conservazione' },
    { id: 'sharing' as const, label: 'Condivisioni' },
    { id: 'activity' as const, label: 'Attività' },
    ...(user?.role === 'ADMIN' ? [{ id: 'permissions' as const, label: 'Permessi' }] : []),
  ]

  return (
    <>
      <div className="flex h-full flex-col border-l border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="truncate text-lg font-semibold text-slate-800">{doc.title}</h2>
          <div className="flex items-center gap-2">
            <DocumentChatButton documentId={doc.id} documentTitle={doc.title} />
            {onVisualize && (
              <button
                type="button"
                onClick={onVisualize}
                className="rounded bg-slate-100 px-2 py-1 text-sm text-slate-700 hover:bg-slate-200"
              >
                Visualizza
              </button>
            )}
            <button
              type="button"
              onClick={() => setShareModalOpen(true)}
              className="rounded bg-indigo-100 px-2 py-1 text-sm text-indigo-700 hover:bg-indigo-200"
            >
              Condividi
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded p-1 text-slate-500 hover:bg-slate-100"
              aria-label="Chiudi"
            >
              ✕
            </button>
          </div>
        </div>
        <DocumentLockBadge
          lockedBy={doc.locked_by ? { id: String(doc.locked_by) } : null}
          isCurrentUser={!!isLockedByMe}
          onUnlock={handleUnlock}
          unlocking={unlocking}
        />
        <div className="border-b border-slate-200 px-4">
          <nav className="flex gap-4">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={`border-b-2 py-2 text-sm font-medium ${tab === t.id ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-600 hover:text-slate-800'}`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
        <div className="flex-1 overflow-auto p-4">
          {tab === 'info' && (
            <div className="space-y-3 text-sm">
              <p><span className="font-medium text-slate-600">Stato:</span> {doc.status}</p>
              <p><span className="font-medium text-slate-600">Versione corrente:</span> {doc.current_version}</p>
              {doc.description && (
                <p><span className="font-medium text-slate-600">Descrizione:</span> {doc.description}</p>
              )}
              <div className="flex flex-wrap gap-2 pt-2">
                <button
                  type="button"
                  onClick={handleDownload}
                  className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700"
                >
                  Scarica
                </button>
                {(doc.can_write !== false || user?.role === 'ADMIN') && (
                  <button
                    type="button"
                    onClick={() => onNewVersion(doc)}
                    className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-300"
                  >
                    Nuova versione
                  </button>
                )}
              </div>
            </div>
          )}
          {tab === 'versions' && (
            <div>
              <button
                type="button"
                onClick={() => {
                  getDocumentVersions(doc.id).then((v) => {
                    setVersions(v)
                    setVersionModalOpen(true)
                  })
                }}
                className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-300"
              >
                Apri storico versioni
              </button>
              <ul className="mt-3 space-y-2">
                {(versions ?? doc.versions ?? []).slice(0, 5).map((v) => (
                  <li key={v.id} className="flex items-center justify-between rounded border border-slate-100 px-2 py-1.5 text-sm">
                    <span>v{v.version_number} — {v.file_name}</span>
                    <button
                      type="button"
                      onClick={() => downloadDocument(doc.id, v.version_number, v.file_name)}
                      className="text-indigo-600 hover:underline"
                    >
                      Scarica
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {tab === 'metadata' && metadataStructureId && (
            <div className="space-y-3">
              {!metadataStructure && (
                <p className="text-sm text-slate-500">Caricamento struttura...</p>
              )}
              {metadataStructure && (
                <>
                  {!metadataEdit ? (
                    <>
                      <DynamicMetadataForm
                        structure={metadataStructure}
                        values={metadataValues}
                        onChange={() => {}}
                        readOnly
                      />
                      {(doc.can_write || user?.role === 'ADMIN') && (
                        <button
                          type="button"
                          onClick={() => {
                            loadMetadataStructure()
                            setMetadataEditValues({ ...metadataValues })
                            setMetadataEdit(true)
                          }}
                          className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-300"
                        >
                          Modifica metadati
                        </button>
                      )}
                    </>
                  ) : (
                    <>
                      <DynamicMetadataForm
                        structure={metadataStructure}
                        values={metadataEditValues}
                        onChange={setMetadataEditValues}
                        errors={metadataErrors}
                      />
                      <div className="flex gap-2">
                        <button
                          type="button"
                          disabled={metadataSaving}
                          onClick={async () => {
                            if (!doc) return
                            setMetadataSaving(true)
                            setMetadataErrors({})
                            try {
                              await updateDocumentMetadata(doc.id, metadataEditValues)
                              onRefresh()
                              setMetadataEdit(false)
                            } catch (err: unknown) {
                              const data = (err as { response?: { data?: { metadata_values?: Record<string, string> } } })?.response?.data
                              setMetadataErrors(data?.metadata_values ?? {})
                            } finally {
                              setMetadataSaving(false)
                            }
                          }}
                          className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
                        >
                          {metadataSaving ? 'Salvataggio...' : 'Salva'}
                        </button>
                        <button
                          type="button"
                          onClick={() => setMetadataEdit(false)}
                          className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-300"
                        >
                          Annulla
                        </button>
                      </div>
                    </>
                  )}
                </>
              )}
            </div>
          )}
          {tab === 'attachments' && (
            <div className="space-y-3">
              <form onSubmit={handleUploadAttachment} className="flex flex-wrap items-end gap-2">
                <input
                  type="file"
                  onChange={(e) => setAttachFile(e.target.files?.[0] ?? null)}
                  className="text-sm"
                />
                <input
                  type="text"
                  value={attachDesc}
                  onChange={(e) => setAttachDesc(e.target.value)}
                  placeholder="Descrizione"
                  className="rounded border border-slate-300 px-2 py-1 text-sm"
                />
                <button
                  type="submit"
                  disabled={!attachFile}
                  className="rounded bg-indigo-600 px-3 py-1 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  Carica
                </button>
              </form>
              <ul className="space-y-1">
                {(attachments ?? []).map((att) => (
                  <li key={att.id} className="flex items-center justify-between rounded border border-slate-100 px-2 py-1.5 text-sm">
                    <span>{att.file_name}</span>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => downloadAttachment(doc.id, att.id, att.file_name)}
                        className="text-indigo-600 hover:underline"
                      >
                        Scarica
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteAttachment(att.id)}
                        className="text-red-600 hover:underline"
                      >
                        Elimina
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {tab === 'protocols' && (
            <div className="space-y-3 text-sm">
              {doc.is_protocolled ? (
                <p className="text-slate-600">Questo documento è stato protocollato e non è modificabile.</p>
              ) : (
                <>
                  <p className="text-slate-600">Protocolla questo documento (in uscita) per registrarlo e bloccarne le modifiche.</p>
                  <button
                    type="button"
                    onClick={() => setProtocolModalOpen(true)}
                    className="rounded bg-indigo-600 px-3 py-1.5 text-white hover:bg-indigo-700"
                  >
                    Protocolla
                  </button>
                </>
              )}
            </div>
          )}
          {tab === 'signatures' && (
            <div className="space-y-3 text-sm">
              <p className="text-slate-600">Storico richieste di firma digitale. Documento deve essere Approvato e la struttura metadati deve avere firma abilitata.</p>
              <ul className="space-y-2">
                {signaturesList.map((s) => (
                  <li key={s.id} className="flex items-center justify-between rounded border border-slate-200 px-3 py-2">
                    <span>{s.signer_email ?? s.signer} — {s.format} — {s.status}</span>
                    {s.status === 'completed' && s.signed_at && (
                      <span className="text-xs text-slate-500">{new Date(s.signed_at).toLocaleString('it-IT')}</span>
                    )}
                  </li>
                ))}
              </ul>
              {signaturesList.length === 0 && <p className="text-slate-500">Nessuna richiesta di firma.</p>}
            </div>
          )}
          {tab === 'conservation' && (
            <div className="space-y-3 text-sm">
              <p className="text-slate-600">Invio in conservazione digitale. Prerequisiti: documento Approvato e almeno una firma completata.</p>
              <ul className="space-y-2">
                {conservationList.map((c) => (
                  <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-200 px-3 py-2">
                    <span>Stato: {c.status} — {c.document_type} ({c.document_date})</span>
                    {['sent', 'in_progress'].includes(c.status) && (
                      <button
                        type="button"
                        onClick={() => {
                          checkConservationStatus(c.id).then(() => {
                            getDocumentConservation(doc.id).then(setConservationList)
                          }).catch(() => {})
                        }}
                        className="rounded bg-slate-200 px-2 py-1 text-xs hover:bg-slate-300"
                      >
                        Verifica stato
                      </button>
                    )}
                    {c.status === 'completed' && c.certificate_url && (
                      <a href={c.certificate_url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 text-xs hover:underline">
                        Scarica attestato
                      </a>
                    )}
                  </li>
                ))}
              </ul>
              {conservationList.length === 0 && <p className="text-slate-500">Nessuna richiesta di conservazione.</p>}
            </div>
          )}
          {tab === 'sharing' && (
            <div className="space-y-3 text-sm">
              <ShareListPanel
                shares={sharesList}
                onRevoke={async (shareId) => {
                  await revokeShare(shareId)
                  getDocumentShares(doc.id).then(setSharesList)
                }}
                onNewShare={() => setShareModalOpen(true)}
              />
            </div>
          )}
          {tab === 'activity' && (
            <div className="space-y-3 text-sm">
              <ActivityTimeline items={activityList} />
            </div>
          )}
          {tab === 'permissions' && (
            <p className="text-sm text-slate-600">Gestione permessi (solo metadati: can_read, can_write, can_delete).</p>
          )}
        </div>
      </div>
      <ProtocolFormModal
        isOpen={protocolModalOpen}
        onClose={() => setProtocolModalOpen(false)}
        linkedDocument={doc}
        onSubmit={async () => {
          onRefresh()
        }}
      />
      <ShareModal
        open={shareModalOpen}
        onClose={() => setShareModalOpen(false)}
        onSuccess={() => {
          getDocumentShares(doc.id).then(setSharesList)
        }}
        shareDocument={shareDocument}
        targetId={doc.id}
        targetLabel={doc.title}
      />
      <VersionHistoryModal
        open={versionModalOpen}
        onClose={() => setVersionModalOpen(false)}
        documentId={doc.id}
        title={doc.title}
        versions={versions ?? doc.versions ?? []}
      />
    </>
  )
}
