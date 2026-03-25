import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getDossierDetail,
  archiveDossier,
  addDossierDocument,
  removeDossierDocument,
  addDossierProtocol,
  removeDossierProtocol,
  addDossierFolder,
  removeDossierFolder,
  uploadDossierFile,
  closeDossier,
  generateDossierIndex,
  updateDossier,
  addDossierEmail,
} from '../services/dossierService'
import type { DossierDetailItem, DossierEmailEntry } from '../services/dossierService'
import { EntityMetadataPanel } from '../components/metadata/EntityMetadataPanel'
import { SignaturePanel } from '../components/signatures/SignaturePanel'
import { ActivityTimeline } from '../components/audit/ActivityTimeline'
import { useAuthStore } from '../store/authStore'
import { getAuditLog } from '../services/auditService'
import type { AuditLogItem } from '../services/auditService'
import { getDocuments, getFolders, createFolder } from '../services/documentService'
import type { DocumentItem, FolderItem } from '../services/documentService'
import { getProtocols } from '../services/protocolService'
import type { ProtocolItem } from '../services/protocolService'
import { getUsers } from '../services/userService'
import { useBreadcrumbTitle } from '../components/layout/BreadcrumbContext'
import { getMailMessages } from '../services/mailService'
import type { MailMessageItem } from '../services/mailService'

type TabId = 'documents' | 'protocols' | 'emails' | 'metadata' | 'signature' | 'history'

const TABS: { id: TabId; label: string }[] = [
  { id: 'documents', label: 'Documenti' },
  { id: 'protocols', label: 'Protocolli' },
  { id: 'emails', label: 'Email/PEC' },
  { id: 'metadata', label: 'Metadati AGID' },
  { id: 'signature', label: 'Documenti firmati' },
  { id: 'history', label: 'Log' },
]

export function DossierDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [dossier, setDossier] = useState<DossierDetailItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<TabId>('documents')
  const [archiving, setArchiving] = useState(false)
  const [closing, setClosing] = useState(false)
  const [generatingIndex, setGeneratingIndex] = useState(false)
  const [activityItems, setActivityItems] = useState<AuditLogItem[]>([])
  const [emailExpanded, setEmailExpanded] = useState<number | null>(null)
  const [availableDocs, setAvailableDocs] = useState<DocumentItem[]>([])
  const [availableFolders, setAvailableFolders] = useState<FolderItem[]>([])
  const [availableProtocols, setAvailableProtocols] = useState<ProtocolItem[]>([])
  const [allUsers, setAllUsers] = useState<
    {
      id: string
      email: string
      first_name?: string
      last_name?: string
      organizational_units?: Array<{ id: string; name: string; code: string }>
    }[]
  >([])
  const [docSearch, setDocSearch] = useState('')
  const [docDropdownOpen, setDocDropdownOpen] = useState(false)
  const [folderSearch, setFolderSearch] = useState('')
  const [folderDropdownOpen, setFolderDropdownOpen] = useState(false)
  const [protoSearch, setProtoSearch] = useState('')
  const [protoDropdownOpen, setProtoDropdownOpen] = useState(false)
  const [permissionsOpen, setPermissionsOpen] = useState(false)
  const [mailMessages, setMailMessages] = useState<MailMessageItem[]>([])
  const [mailSearch, setMailSearch] = useState('')
  const [mailTypeFilter, setMailTypeFilter] = useState<'all' | 'email' | 'pec'>('all')
  const [mailLoading, setMailLoading] = useState(false)
  const [addingEmail, setAddingEmail] = useState(false)
  const user = useAuthStore((s) => s.user)
  const { setEntityTitle } = useBreadcrumbTitle()

  const load = useCallback(() => {
    if (!id) return
    setLoading(true)
    getDossierDetail(id)
      .then(setDossier)
      .catch(() => setDossier(null))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!dossier) {
      setEntityTitle(null)
      return
    }
    setEntityTitle(dossier.identifier || dossier.title || null)
    return () => setEntityTitle(null)
  }, [dossier, setEntityTitle])

  useEffect(() => {
    getDocuments({ page: 1 }).then((r) => setAvailableDocs(r.results || [])).catch(() => setAvailableDocs([]))
    getFolders({ all: 'true' }).then(setAvailableFolders).catch(() => setAvailableFolders([]))
    getProtocols({}).then((r) => setAvailableProtocols(r.results || [])).catch(() => setAvailableProtocols([]))
    getUsers({}).then((r) => setAllUsers(r.results || [])).catch(() => setAllUsers([]))
  }, [])

  useEffect(() => {
    const handleClickOutside = () => {
      setTimeout(() => {
        setDocDropdownOpen(false)
        setFolderDropdownOpen(false)
        setProtoDropdownOpen(false)
      }, 200)
    }
    document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [])

  useEffect(() => {
    if (tab === 'history' && id) {
      getAuditLog({ target_type: 'dossier', target_id: id, page_size: 50 })
        .then((res) => setActivityItems(res.results ?? []))
        .catch(() => setActivityItems([]))
    }
  }, [tab, id])

  useEffect(() => {
    if (tab === 'emails') {
      setMailLoading(true)
      getMailMessages({})
        .then((r) => setMailMessages(r.results || []))
        .catch(() => setMailMessages([]))
        .finally(() => setMailLoading(false))
    }
  }, [tab])

  const handleArchive = async () => {
    if (!dossier || !confirm('Archiviare questo fascicolo? Tutti i documenti devono essere approvati.')) return
    setArchiving(true)
    try {
      await archiveDossier(dossier.id)
      load()
    } catch (e) {
      alert((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Errore')
    } finally {
      setArchiving(false)
    }
  }

  const handleClose = async () => {
    if (!dossier || !confirm('Chiudere definitivamente questo fascicolo? Non sarà possibile aggiungere nuovi documenti.')) return
    setClosing(true)
    try {
      await closeDossier(dossier.id)
      load()
    } catch (e) {
      alert((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Errore')
    } finally {
      setClosing(false)
    }
  }

  const handleGenerateIndex = async () => {
    if (!dossier) return
    setGeneratingIndex(true)
    try {
      const blob = await generateDossierIndex(dossier.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `indice_${dossier.identifier || dossier.id}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      load()
    } catch (e) {
      alert('Errore generazione indice.')
    } finally {
      setGeneratingIndex(false)
    }
  }

  const handleRemoveDocument = async (docId: string) => {
    if (!dossier || !confirm('Rimuovere il documento dal fascicolo?')) return
    try {
      await removeDossierDocument(dossier.id, docId)
      load()
    } catch {
      alert('Errore')
    }
  }

  const handleRemoveFolder = async (dossierFolderId: string) => {
    if (!dossier || !confirm('Rimuovere la cartella dal fascicolo?')) return
    try {
      await removeDossierFolder(dossier.id, dossierFolderId)
      load()
    } catch {
      alert('Errore')
    }
  }

  const handleChangeResponsible = async (userId: string) => {
    if (!dossier) return
    try {
      await updateDossier(dossier.id, { responsible: userId || undefined })
      load()
    } catch {
      alert('Errore aggiornamento responsabile.')
    }
  }

  const handleToggleUserPermission = async (userId: string) => {
    if (!dossier) return
    const currentIds = dossier.allowed_user_ids || []
    const newIds = currentIds.includes(userId)
      ? currentIds.filter((x) => x !== userId)
      : [...currentIds, userId]
    try {
      await updateDossier(dossier.id, { allowed_users: newIds })
      load()
    } catch {
      alert('Errore aggiornamento permessi.')
    }
  }

  const handleRemoveProtocol = async (protoId: string) => {
    if (!dossier || !confirm('Rimuovere il protocollo dal fascicolo?')) return
    try {
      await removeDossierProtocol(dossier.id, protoId)
      load()
    } catch {
      alert('Errore')
    }
  }

  const handleUploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!dossier || !e.target.files?.[0]) return
    const file = e.target.files[0]
    try {
      await uploadDossierFile(dossier.id, file)
      e.target.value = ''
      load()
    } catch (err) {
      alert('Errore caricamento file.')
    }
  }

  const handleAttachEmail = async (email: MailMessageItem) => {
    if (!dossier) return
    setAddingEmail(true)
    try {
      await addDossierEmail(dossier.id, {
        email_type: email.account_type === 'pec' ? 'pec' : 'email',
        from_address: email.from_address,
        to_addresses: email.to_addresses?.map((a) => a.email) || [],
        subject: email.subject,
        body: '',
        received_at: email.sent_at || undefined,
        message_id: email.id,
      })
      load()
    } catch (e) {
      alert(
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Errore aggiunta email.',
      )
    } finally {
      setAddingEmail(false)
    }
  }

  if (loading || !dossier) {
    return (
      <div className="p-6">
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Caricamento...</p>
        ) : (
          <p className="text-slate-500 dark:text-slate-400">Fascicolo non trovato.</p>
        )}
      </div>
    )
  }

  const canEditDossier = user?.role === 'ADMIN' || user?.role === 'APPROVER' || String(dossier.responsible) === String(user?.id)
  const isOpen = dossier.status === 'open'
  const dossierMetaId = typeof dossier.metadata_structure === 'object' && dossier.metadata_structure != null
    ? (dossier.metadata_structure as { id: string }).id
    : (dossier.metadata_structure as string) || null

  const statusBadge =
    dossier.status === 'closed'
      ? 'bg-slate-200 text-slate-700 dark:bg-slate-600 dark:text-slate-100'
      : dossier.status === 'archived'
        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200'
        : 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
  const statusLabel = dossier.status === 'closed' ? 'Chiuso' : dossier.status === 'archived' ? 'Archiviato' : 'Aperto'

  return (
    <div className="flex flex-col rounded-lg border border-slate-200 bg-white shadow dark:border-slate-700 dark:bg-slate-800">
      <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <button
              type="button"
              onClick={() => navigate('/dossiers')}
              className="text-sm text-indigo-600 hover:underline dark:text-indigo-400"
            >
              ← Fascicoli
            </button>
            <p className="mt-1 font-mono text-lg font-semibold text-slate-800 dark:text-slate-100">{dossier.identifier}</p>
            <h1 className="mt-0.5 text-xl font-semibold text-slate-800 dark:text-slate-100">{dossier.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${statusBadge}`}>{statusLabel}</span>
              <span className="text-sm text-slate-600 dark:text-slate-300">
                Responsabile: {dossier.responsible_email || '—'}
              </span>
              {dossier.organizational_unit_code && (
                <span className="text-sm text-slate-500 dark:text-slate-400">U.O.: {dossier.organizational_unit_code}</span>
              )}
            </div>
            {isOpen && canEditDossier && (
              <button
                type="button"
                onClick={() => setPermissionsOpen(!permissionsOpen)}
                className="mt-2 text-xs text-indigo-600 hover:underline dark:text-indigo-400"
              >
                {permissionsOpen ? '▼ Chiudi gestione accessi' : '▶ Gestione responsabile e permessi'}
              </button>
            )}
            {permissionsOpen && (
              <div className="mt-3 space-y-3 rounded border border-slate-200 bg-slate-50 p-3 dark:border-slate-600 dark:bg-slate-900/40">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                    Responsabile del fascicolo
                  </label>
                  <select
                    value={dossier.responsible || ''}
                    onChange={(e) => handleChangeResponsible(e.target.value)}
                    className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
                  >
                    <option value="">— Nessuno —</option>
                    {allUsers.map((u) => {
                      const ous = u.organizational_units || []
                      const ouLabel = ous.length > 0 ? ` [${ous.map((o) => o.name).join(', ')}]` : ''
                      return (
                        <option key={u.id} value={u.id}>
                          {u.first_name} {u.last_name} ({u.email}){ouLabel}
                        </option>
                      )
                    })}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                    Utenti con accesso al fascicolo
                  </label>
                  <div className="max-h-48 overflow-y-auto rounded border border-white bg-white dark:border-slate-600 dark:bg-slate-800">
                    {allUsers.map((u) => {
                      const hasAccess = (dossier.allowed_user_ids || []).includes(u.id)
                      const ous = u.organizational_units || []
                      return (
                        <label
                          key={u.id}
                          className={`flex cursor-pointer items-center gap-2 border-b border-slate-100 px-3 py-1.5 hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-700/50 ${hasAccess ? 'bg-indigo-50/50 dark:bg-indigo-950/30' : ''}`}
                        >
                          <input
                            type="checkbox"
                            checked={hasAccess}
                            onChange={() => handleToggleUserPermission(u.id)}
                          />
                          <div className="min-w-0 flex-1">
                            <span className="text-sm text-slate-800 dark:text-slate-100">
                              {u.first_name} {u.last_name}
                            </span>
                            <span className="ml-1 text-xs text-slate-500 dark:text-slate-400">({u.email})</span>
                            {ous.length > 0 && (
                              <span className="ml-1 text-xs text-indigo-500 dark:text-indigo-400">
                                [{ous.map((o) => o.name).join(', ')}]
                              </span>
                            )}
                          </div>
                        </label>
                      )
                    })}
                  </div>
                  <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                    {(dossier.allowed_user_ids || []).length} utenti con accesso
                  </p>
                </div>
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {isOpen && (
              <>
                <button
                  type="button"
                  onClick={handleClose}
                  disabled={closing || !canEditDossier}
                  className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 dark:hover:bg-slate-600"
                >
                  {closing ? 'Chiusura...' : 'Chiudi fascicolo'}
                </button>
                <button
                  type="button"
                  onClick={handleArchive}
                  disabled={archiving || !canEditDossier}
                  className="rounded bg-amber-100 px-3 py-1.5 text-sm font-medium text-amber-800 hover:bg-amber-200 disabled:opacity-50 dark:bg-amber-900/40 dark:text-amber-200 dark:hover:bg-amber-900/60"
                >
                  {archiving ? 'Archiviazione...' : 'Archivia fascicolo'}
                </button>
              </>
            )}
            <button
              type="button"
              onClick={handleGenerateIndex}
              disabled={generatingIndex}
              className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 dark:hover:bg-indigo-500"
            >
              {generatingIndex ? 'Generazione...' : 'Genera indice'}
            </button>
            {dossier.index_file && (
              <a
                href={dossier.index_file}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 dark:hover:bg-slate-600"
              >
                Scarica indice PDF
              </a>
            )}
          </div>
        </div>
        <div className="mt-3 grid gap-2 text-sm text-slate-600 dark:text-slate-300 sm:grid-cols-2 lg:grid-cols-4">
          {dossier.classification_code && (
            <p><strong>Classificazione:</strong> {dossier.classification_code} {dossier.classification_label || ''}</p>
          )}
          <p><strong>Data apertura:</strong> {dossier.created_at ? new Date(dossier.created_at).toLocaleDateString('it-IT') : '—'}</p>
          {dossier.closed_at && <p><strong>Data chiusura:</strong> {new Date(dossier.closed_at).toLocaleDateString('it-IT')}</p>}
          {(dossier.retention_years ?? 0) > 0 && <p><strong>Conservazione:</strong> {dossier.retention_years} anni</p>}
        </div>
      </div>

      <div className="flex gap-2 overflow-x-auto border-b border-slate-200 px-4 dark:border-slate-700">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`shrink-0 border-b-2 px-3 py-2 text-sm font-medium ${
              tab === t.id
                ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                : 'border-transparent text-slate-600 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="min-h-[200px] p-4">
        {tab === 'documents' && (
          <div className="space-y-4">
            {isOpen && canEditDossier && (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-3">
                  <div className="relative min-w-[250px] flex-1" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="text"
                      placeholder="🔍 Cerca documento per titolo..."
                      value={docSearch}
                      onChange={(e) => {
                        setDocSearch(e.target.value)
                        setDocDropdownOpen(true)
                      }}
                      onFocus={() => setDocDropdownOpen(true)}
                      className="w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
                    />
                    {docDropdownOpen && (
                      <div className="absolute z-20 mt-1 max-h-48 w-full overflow-y-auto rounded border border-slate-200 bg-white shadow-lg dark:border-slate-600 dark:bg-slate-800">
                        {availableDocs
                          .filter((d) => !dossier.documents?.some((dd) => dd.document_id === d.id))
                          .filter((d) => !docSearch.trim() || d.title.toLowerCase().includes(docSearch.toLowerCase()))
                          .map((d) => (
                            <button
                              key={d.id}
                              type="button"
                              onClick={async () => {
                                setDocSearch('')
                                setDocDropdownOpen(false)
                                try {
                                  await addDossierDocument(dossier.id, d.id)
                                  load()
                                  getDocuments({ page: 1 }).then((r) => setAvailableDocs(r.results || []))
                                } catch (e) {
                                  alert(
                                    (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
                                      'Errore',
                                  )
                                }
                              }}
                              className="flex w-full items-center px-3 py-2 text-left text-sm hover:bg-indigo-50 dark:hover:bg-indigo-950/40"
                            >
                              <span className="truncate text-slate-800 dark:text-slate-100">{d.title}</span>
                            </button>
                          ))}
                        {availableDocs
                          .filter((d) => !dossier.documents?.some((dd) => dd.document_id === d.id))
                          .filter((d) => !docSearch.trim() || d.title.toLowerCase().includes(docSearch.toLowerCase()))
                          .length === 0 && (
                          <p className="px-3 py-2 text-sm text-slate-400 dark:text-slate-500">Nessun documento trovato</p>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="relative min-w-[200px] flex-1" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="text"
                      placeholder="🔍 Cerca o crea cartella..."
                      value={folderSearch}
                      onChange={(e) => {
                        setFolderSearch(e.target.value)
                        setFolderDropdownOpen(true)
                      }}
                      onFocus={() => setFolderDropdownOpen(true)}
                      className="w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
                    />
                    {folderDropdownOpen && (
                      <div className="absolute z-20 mt-1 max-h-48 w-full overflow-y-auto rounded border border-slate-200 bg-white shadow-lg dark:border-slate-600 dark:bg-slate-800">
                        {availableFolders
                          .filter((f) => !dossier.dossier_folders?.some((df) => df.folder === f.id))
                          .filter((f) => !folderSearch.trim() || f.name.toLowerCase().includes(folderSearch.toLowerCase()))
                          .map((f) => (
                            <button
                              key={f.id}
                              type="button"
                              onClick={async () => {
                                setFolderSearch('')
                                setFolderDropdownOpen(false)
                                try {
                                  await addDossierFolder(dossier.id, f.id)
                                  load()
                                } catch (e) {
                                  alert(
                                    (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
                                      'Errore',
                                  )
                                }
                              }}
                              className="flex w-full items-center px-3 py-2 text-left text-sm hover:bg-indigo-50 dark:hover:bg-indigo-950/40"
                            >
                              📁 <span className="ml-1 truncate text-slate-800 dark:text-slate-100">{f.name}</span>
                            </button>
                          ))}
                        {folderSearch.trim() && (
                          <button
                            type="button"
                            onClick={async () => {
                              setFolderDropdownOpen(false)
                              try {
                                const folder = await createFolder({ name: folderSearch.trim(), parent_id: null })
                                await addDossierFolder(dossier.id, folder.id)
                                setFolderSearch('')
                                load()
                                getFolders({ all: 'true' }).then(setAvailableFolders)
                              } catch {
                                alert('Errore creazione cartella.')
                              }
                            }}
                            className="flex w-full items-center border-t border-slate-100 px-3 py-2 text-left text-sm font-medium text-indigo-600 hover:bg-indigo-50 dark:border-slate-600 dark:text-indigo-400 dark:hover:bg-indigo-950/40"
                          >
                            {`+ Crea cartella "${folderSearch.trim()}"`}
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  <label className="shrink-0 cursor-pointer rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 dark:hover:bg-indigo-500">
                    📤 Carica file
                    <input type="file" className="hidden" onChange={handleUploadFile} />
                  </label>
                </div>
              </div>
            )}

            <div>
              <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Documenti ({dossier.documents?.length || 0})
              </h3>
              <ul className="mt-2 space-y-1">
                {dossier.documents?.map((d) => (
                  <li
                    key={d.id}
                    className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-700/40"
                  >
                    <span className="text-slate-800 dark:text-slate-100">{d.document_title || d.document_id}</span>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => navigate(`/documents?doc=${d.document_id}`)}
                        className="text-xs text-indigo-600 hover:underline dark:text-indigo-400"
                      >
                        Apri
                      </button>
                      {isOpen && canEditDossier && (
                        <button
                          type="button"
                          onClick={() => handleRemoveDocument(d.document_id)}
                          className="text-xs text-red-600 hover:underline dark:text-red-400"
                        >
                          Rimuovi
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
              {(!dossier.documents || dossier.documents.length === 0) && (
                <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Nessun documento.</p>
              )}
            </div>

            {dossier.dossier_folders && dossier.dossier_folders.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Cartelle collegate ({dossier.dossier_folders.length})
                </h3>
                <ul className="mt-2 space-y-1">
                  {dossier.dossier_folders.map((df) => (
                    <li
                      key={df.id}
                      className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-700/40"
                    >
                      <span className="text-slate-800 dark:text-slate-100">📁 {df.folder_name || df.folder}</span>
                      {isOpen && canEditDossier && (
                        <button
                          type="button"
                          onClick={() => handleRemoveFolder(String(df.id))}
                          className="text-xs text-red-600 hover:underline dark:text-red-400"
                        >
                          Rimuovi
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {dossier.dossier_files && dossier.dossier_files.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  File caricati ({dossier.dossier_files.length})
                </h3>
                <ul className="mt-2 space-y-1">
                  {dossier.dossier_files.map((f) => (
                    <li
                      key={f.id}
                      className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-700/40"
                    >
                      <span className="text-slate-800 dark:text-slate-100">
                        {f.file_name} ({(f.file_size / 1024).toFixed(1)} KB)
                      </span>
                      {f.file && (
                        <a
                          href={f.file}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-indigo-600 hover:underline dark:text-indigo-400"
                        >
                          Scarica
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {tab === 'protocols' && (
          <div>
            {isOpen && canEditDossier && (
              <div className="relative mb-3 max-w-md" onClick={(e) => e.stopPropagation()}>
                <input
                  type="text"
                  placeholder="🔍 Cerca protocollo per ID o oggetto..."
                  value={protoSearch}
                  onChange={(e) => {
                    setProtoSearch(e.target.value)
                    setProtoDropdownOpen(true)
                  }}
                  onFocus={() => setProtoDropdownOpen(true)}
                  className="w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
                />
                {protoDropdownOpen && (
                  <div className="absolute z-20 mt-1 max-h-48 w-full overflow-y-auto rounded border border-slate-200 bg-white shadow-lg dark:border-slate-600 dark:bg-slate-800">
                    {availableProtocols
                      .filter((p) => !dossier.protocols?.some((dp) => dp.protocol_id === p.id))
                      .filter((p) => {
                        if (!protoSearch.trim()) return true
                        const s = protoSearch.toLowerCase()
                        return (
                          (p.protocol_id || '').toLowerCase().includes(s) ||
                          (p.subject || '').toLowerCase().includes(s)
                        )
                      })
                      .map((p) => (
                        <button
                          key={p.id}
                          type="button"
                          onClick={async () => {
                            setProtoSearch('')
                            setProtoDropdownOpen(false)
                            try {
                              await addDossierProtocol(dossier.id, p.id)
                              load()
                            } catch (e) {
                              alert(
                                (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
                                  'Errore',
                              )
                            }
                          }}
                          className="flex w-full flex-col px-3 py-2 text-left text-sm hover:bg-indigo-50 dark:hover:bg-indigo-950/40"
                        >
                          <span className="font-mono text-slate-700 dark:text-slate-200">
                            {p.protocol_id || p.protocol_display}
                          </span>
                          <span className="truncate text-xs text-slate-500 dark:text-slate-400">
                            {p.subject || '(senza oggetto)'}
                          </span>
                        </button>
                      ))}
                    {availableProtocols
                      .filter((p) => !dossier.protocols?.some((dp) => dp.protocol_id === p.id))
                      .filter(
                        (p) =>
                          !protoSearch.trim() ||
                          (p.protocol_id || '').toLowerCase().includes(protoSearch.toLowerCase()) ||
                          (p.subject || '').toLowerCase().includes(protoSearch.toLowerCase()),
                      ).length === 0 && (
                      <p className="px-3 py-2 text-sm text-slate-400 dark:text-slate-500">Nessun protocollo trovato</p>
                    )}
                  </div>
                )}
              </div>
            )}
            <ul className="space-y-1">
              {dossier.protocols?.map((p) => (
                <li
                  key={p.id}
                  className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-700/40"
                >
                  <span className="font-mono text-slate-700 dark:text-slate-200">{p.protocol_display || p.protocol_id}</span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => navigate(`/protocols/${p.protocol_id}`)}
                      className="text-xs text-indigo-600 hover:underline dark:text-indigo-400"
                    >
                      Apri
                    </button>
                    {isOpen && canEditDossier && (
                      <button
                        type="button"
                        onClick={() => handleRemoveProtocol(p.protocol_id)}
                        className="text-xs text-red-600 hover:underline dark:text-red-400"
                      >
                        Rimuovi
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            {(!dossier.protocols || dossier.protocols.length === 0) && (
              <p className="text-sm text-slate-500 dark:text-slate-400">Nessun protocollo collegato.</p>
            )}
          </div>
        )}

        {tab === 'emails' && (
          <div className="space-y-4">
            {isOpen && canEditDossier && (
              <div className="space-y-2">
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  Cerca e allega email o PEC dal client di posta al fascicolo.
                </p>
                <div className="flex flex-wrap gap-2">
                  <input
                    type="text"
                    placeholder="🔍 Cerca per oggetto o mittente..."
                    value={mailSearch}
                    onChange={(e) => setMailSearch(e.target.value)}
                    className="min-w-[200px] flex-1 rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
                  />
                  <div className="flex rounded border border-slate-200 bg-slate-50 dark:border-slate-600 dark:bg-slate-900/40">
                    {(
                      [
                        { id: 'all' as const, label: 'Tutte' },
                        { id: 'email' as const, label: '📧 Email' },
                        { id: 'pec' as const, label: '🔐 PEC' },
                      ] as const
                    ).map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => setMailTypeFilter(t.id)}
                        className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                          mailTypeFilter === t.id
                            ? 'rounded bg-indigo-600 text-white dark:bg-indigo-500'
                            : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700'
                        }`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>

                {mailLoading ? (
                  <p className="text-sm text-slate-500 dark:text-slate-400">Caricamento email...</p>
                ) : (
                  <div className="max-h-64 overflow-y-auto rounded border border-slate-200 dark:border-slate-600">
                    {mailMessages
                      .filter((m) => {
                        if (mailTypeFilter === 'email') return m.account_type === 'email'
                        if (mailTypeFilter === 'pec') return m.account_type === 'pec'
                        return true
                      })
                      .filter((m) => {
                        if (!mailSearch.trim()) return true
                        const s = mailSearch.toLowerCase()
                        return (
                          m.subject.toLowerCase().includes(s) ||
                          m.from_address.toLowerCase().includes(s) ||
                          (m.from_name || '').toLowerCase().includes(s)
                        )
                      })
                      .map((m) => {
                        const alreadyAttached = (dossier.dossier_emails ?? []).some(
                          (de) => de.message_id === m.id || de.subject === m.subject,
                        )
                        return (
                          <div
                            key={m.id}
                            className={`flex items-center justify-between border-b border-slate-100 px-3 py-2 dark:border-slate-600 ${
                              alreadyAttached
                                ? 'bg-green-50/50 dark:bg-green-950/25'
                                : 'hover:bg-slate-50 dark:hover:bg-slate-700/40'
                            }`}
                          >
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2">
                                <span
                                  className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${
                                    m.account_type === 'pec'
                                      ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200'
                                      : 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200'
                                  }`}
                                >
                                  {m.account_type === 'pec' ? '🔐 PEC' : '📧 Email'}
                                </span>
                                <span
                                  className={`rounded px-1.5 py-0.5 text-xs ${
                                    m.direction === 'in'
                                      ? 'bg-slate-100 text-blue-600 dark:bg-slate-700 dark:text-blue-300'
                                      : 'bg-slate-100 text-amber-600 dark:bg-slate-700 dark:text-amber-300'
                                  }`}
                                >
                                  {m.direction === 'in' ? 'Ricevuta' : 'Inviata'}
                                </span>
                              </div>
                              <p className="mt-0.5 truncate text-sm font-medium text-slate-800 dark:text-slate-100">
                                {m.subject || '(senza oggetto)'}
                              </p>
                              <p className="text-xs text-slate-500 dark:text-slate-400">
                                Da: {m.from_name || m.from_address} ·{' '}
                                {m.sent_at ? new Date(m.sent_at).toLocaleString('it-IT') : ''}
                                {m.has_attachments ? ' · 📎' : ''}
                              </p>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleAttachEmail(m)}
                              disabled={alreadyAttached || addingEmail}
                              className={`ml-2 shrink-0 rounded px-3 py-1.5 text-xs font-medium ${
                                alreadyAttached
                                  ? 'cursor-default bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-200'
                                  : 'bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 dark:hover:bg-indigo-500'
                              }`}
                            >
                              {alreadyAttached ? '✓ Allegata' : '+ Allega'}
                            </button>
                          </div>
                        )
                      })}
                    {mailMessages.filter((m) => {
                      if (mailTypeFilter === 'email') return m.account_type === 'email'
                      if (mailTypeFilter === 'pec') return m.account_type === 'pec'
                      return true
                    }).filter((m) => {
                      if (!mailSearch.trim()) return true
                      const s = mailSearch.toLowerCase()
                      return (
                        m.subject.toLowerCase().includes(s) ||
                        m.from_address.toLowerCase().includes(s) ||
                        (m.from_name || '').toLowerCase().includes(s)
                      )
                    }).length === 0 && (
                      <p className="px-3 py-4 text-center text-sm text-slate-400 dark:text-slate-500">
                        Nessuna email trovata. Configura un account nella sezione Posta.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            <div>
              <h3 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                Email/PEC allegate ({(dossier.dossier_emails ?? []).length})
              </h3>
              {(dossier.dossier_emails ?? []).length > 0 ? (
                <ul className="space-y-2">
                  {(dossier.dossier_emails ?? []).map((em: DossierEmailEntry) => (
                    <li key={em.id} className="rounded border border-slate-200 px-3 py-2 text-sm dark:border-slate-600">
                      <button
                        type="button"
                        className="flex w-full items-center justify-between text-left"
                        onClick={() => setEmailExpanded(emailExpanded === em.id ? null : em.id)}
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                              em.email_type === 'pec'
                                ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200'
                                : 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200'
                            }`}
                          >
                            {em.email_type === 'pec' ? '🔐 PEC' : '📧 Email'}
                          </span>
                          <span className="font-medium text-slate-800 dark:text-slate-100">{em.subject}</span>
                        </div>
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          {new Date(em.received_at).toLocaleDateString('it-IT')}
                        </span>
                      </button>
                      {emailExpanded === em.id && (
                        <div className="mt-2 border-t border-slate-100 pt-2 text-slate-600 dark:border-slate-600 dark:text-slate-300">
                          <p>
                            <strong>Da:</strong> {em.from_address}
                          </p>
                          <p>
                            <strong>A:</strong> {(em.to_addresses || []).join(', ') || '—'}
                          </p>
                          <p>
                            <strong>Data:</strong> {new Date(em.received_at).toLocaleString('it-IT')}
                          </p>
                          {em.body && (
                            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">
                              {em.body}
                            </pre>
                          )}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">Nessuna email/PEC allegata al fascicolo.</p>
              )}
            </div>
          </div>
        )}

        {tab === 'metadata' && (
          <EntityMetadataPanel
            entityType="dossier"
            entityId={dossier.id}
            metadataStructureId={dossierMetaId}
            metadataValues={dossier.metadata_values ?? {}}
            canEdit={!!canEditDossier}
            onSave={load}
          />
        )}

        {tab === 'signature' && id && user && (
          <SignaturePanel
            targetType="dossier"
            targetId={id}
            canRequestSignature={!!canEditDossier}
            currentUserId={user.id}
          />
        )}

        {tab === 'history' && (
          <ActivityTimeline items={activityItems} />
        )}
      </div>
    </div>
  )
}
