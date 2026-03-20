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
} from '../services/dossierService'
import type { DossierDetailItem, DossierEmailEntry } from '../services/dossierService'
import { EntityMetadataPanel } from '../components/metadata/EntityMetadataPanel'
import { SignaturePanel } from '../components/signatures/SignaturePanel'
import { ActivityTimeline } from '../components/audit/ActivityTimeline'
import { useAuthStore } from '../store/authStore'
import { getAuditLog } from '../services/auditService'
import type { AuditLogItem } from '../services/auditService'

type TabId = 'documents' | 'protocols' | 'emails' | 'metadata' | 'signature' | 'history'

const TABS: { id: TabId; label: string }[] = [
  { id: 'documents', label: 'Documenti' },
  { id: 'protocols', label: 'Protocolli' },
  { id: 'emails', label: 'Email/PEC' },
  { id: 'metadata', label: 'Metadati AGID' },
  { id: 'signature', label: 'Firma digitale' },
  { id: 'history', label: 'Storico' },
]

export function DossierDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [dossier, setDossier] = useState<DossierDetailItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<TabId>('documents')
  const [addDocId, setAddDocId] = useState('')
  const [addProtoId, setAddProtoId] = useState('')
  const [addFolderId, setAddFolderId] = useState('')
  const [archiving, setArchiving] = useState(false)
  const [closing, setClosing] = useState(false)
  const [generatingIndex, setGeneratingIndex] = useState(false)
  const [activityItems, setActivityItems] = useState<AuditLogItem[]>([])
  const [emailExpanded, setEmailExpanded] = useState<number | null>(null)
  const user = useAuthStore((s) => s.user)

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
    if (tab === 'history' && id) {
      getAuditLog({ target_type: 'dossier', target_id: id, page_size: 50 })
        .then((res) => setActivityItems(res.results ?? []))
        .catch(() => setActivityItems([]))
    }
  }, [tab, id])

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

  const handleAddDocument = async () => {
    if (!dossier || !addDocId.trim()) return
    try {
      await addDossierDocument(dossier.id, addDocId.trim())
      setAddDocId('')
      load()
    } catch (e) {
      alert((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Errore')
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

  const handleAddFolder = async () => {
    if (!dossier || !addFolderId.trim()) return
    try {
      await addDossierFolder(dossier.id, addFolderId.trim())
      setAddFolderId('')
      load()
    } catch (e) {
      alert((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Errore')
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

  const handleAddProtocol = async () => {
    if (!dossier || !addProtoId.trim()) return
    try {
      await addDossierProtocol(dossier.id, addProtoId.trim())
      setAddProtoId('')
      load()
    } catch (e) {
      alert((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Errore')
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

  if (loading || !dossier) {
    return (
      <div className="p-6">
        {loading ? <p className="text-slate-500">Caricamento...</p> : <p className="text-slate-500">Fascicolo non trovato.</p>}
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
      ? 'bg-slate-200 text-slate-700'
      : dossier.status === 'archived'
        ? 'bg-blue-100 text-blue-800'
        : 'bg-green-100 text-green-800'
  const statusLabel = dossier.status === 'closed' ? 'Chiuso' : dossier.status === 'archived' ? 'Archiviato' : 'Aperto'

  return (
    <div className="flex flex-col rounded-lg bg-white shadow">
      <div className="border-b border-slate-200 px-4 py-3">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <button type="button" onClick={() => navigate('/dossiers')} className="text-sm text-indigo-600 hover:underline">
              ← Fascicoli
            </button>
            <p className="mt-1 font-mono text-lg font-semibold text-slate-800">{dossier.identifier}</p>
            <h1 className="mt-0.5 text-xl font-semibold text-slate-800">{dossier.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${statusBadge}`}>{statusLabel}</span>
              <span className="text-sm text-slate-600">Responsabile: {dossier.responsible_email || '—'}</span>
              {dossier.organizational_unit_code && (
                <span className="text-sm text-slate-500">UO: {dossier.organizational_unit_code}</span>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {isOpen && (
              <>
                <button
                  type="button"
                  onClick={handleClose}
                  disabled={closing || !canEditDossier}
                  className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  {closing ? 'Chiusura...' : 'Chiudi fascicolo'}
                </button>
                <button
                  type="button"
                  onClick={handleArchive}
                  disabled={archiving || !canEditDossier}
                  className="rounded bg-amber-100 px-3 py-1.5 text-sm font-medium text-amber-800 hover:bg-amber-200 disabled:opacity-50"
                >
                  {archiving ? 'Archiviazione...' : 'Archivia fascicolo'}
                </button>
              </>
            )}
            <button
              type="button"
              onClick={handleGenerateIndex}
              disabled={generatingIndex}
              className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {generatingIndex ? 'Generazione...' : 'Genera indice'}
            </button>
            {dossier.index_file && (
              <a
                href={dossier.index_file}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Scarica indice PDF
              </a>
            )}
          </div>
        </div>
        <div className="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-2 lg:grid-cols-4">
          {dossier.classification_code && (
            <p><strong>Classificazione:</strong> {dossier.classification_code} {dossier.classification_label || ''}</p>
          )}
          <p><strong>Data apertura:</strong> {dossier.created_at ? new Date(dossier.created_at).toLocaleDateString('it-IT') : '—'}</p>
          {dossier.closed_at && <p><strong>Data chiusura:</strong> {new Date(dossier.closed_at).toLocaleDateString('it-IT')}</p>}
          {(dossier.retention_years ?? 0) > 0 && <p><strong>Conservazione:</strong> {dossier.retention_years} anni</p>}
        </div>
      </div>

      <div className="flex gap-2 border-b border-slate-200 px-4 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`shrink-0 border-b-2 px-3 py-2 text-sm font-medium ${tab === t.id ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-600 hover:text-slate-800'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="min-h-[200px] p-4">
        {tab === 'documents' && (
          <div className="space-y-4">
            {isOpen && canEditDossier && (
              <div className="flex flex-wrap gap-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="ID documento"
                    value={addDocId}
                    onChange={(e) => setAddDocId(e.target.value)}
                    className="rounded border border-slate-300 px-3 py-1.5 text-sm"
                  />
                  <button type="button" onClick={handleAddDocument} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700">
                    Aggiungi documento
                  </button>
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="ID cartella"
                    value={addFolderId}
                    onChange={(e) => setAddFolderId(e.target.value)}
                    className="rounded border border-slate-300 px-3 py-1.5 text-sm"
                  />
                  <button type="button" onClick={handleAddFolder} className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50">
                    Aggiungi cartella
                  </button>
                </div>
                <label className="cursor-pointer rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
                  Aggiungi file
                  <input type="file" className="hidden" onChange={handleUploadFile} />
                </label>
              </div>
            )}
            <div>
              <h3 className="text-sm font-medium text-slate-700">Documenti</h3>
              <ul className="mt-2 space-y-2">
                {dossier.documents?.map((d) => (
                  <li key={d.id} className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm">
                    <span>{d.document_title || d.document_id}</span>
                    {isOpen && canEditDossier && (
                      <button type="button" onClick={() => handleRemoveDocument(d.document_id)} className="text-red-600 hover:underline">
                        Rimuovi
                      </button>
                    )}
                  </li>
                ))}
              </ul>
              {(!dossier.documents || dossier.documents.length === 0) && <p className="mt-2 text-slate-500">Nessun documento.</p>}
            </div>
            {dossier.dossier_folders && dossier.dossier_folders.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-slate-700">Cartelle collegate</h3>
                <ul className="mt-2 space-y-2">
                  {dossier.dossier_folders.map((df) => (
                    <li key={df.id} className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm">
                      <span>{df.folder_name || df.folder}</span>
                      {isOpen && canEditDossier && (
                        <button type="button" onClick={() => handleRemoveFolder(String(df.id))} className="text-red-600 hover:underline">
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
                <h3 className="text-sm font-medium text-slate-700">File caricati</h3>
                <ul className="mt-2 space-y-2">
                  {dossier.dossier_files.map((f) => (
                    <li key={f.id} className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm">
                      <span>{f.file_name} ({(f.file_size / 1024).toFixed(1)} KB)</span>
                      {f.file && (
                        <a href={f.file} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">Scarica</a>
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
              <div className="mb-3 flex gap-2">
                <input
                  type="text"
                  placeholder="ID protocollo"
                  value={addProtoId}
                  onChange={(e) => setAddProtoId(e.target.value)}
                  className="rounded border border-slate-300 px-3 py-1.5 text-sm"
                />
                <button type="button" onClick={handleAddProtocol} className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700">
                  Collega protocollo
                </button>
              </div>
            )}
            <ul className="space-y-2">
              {dossier.protocols?.map((p) => (
                <li key={p.id} className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm">
                  <span>{p.protocol_display || p.protocol_id}</span>
                  {isOpen && canEditDossier && (
                    <button type="button" onClick={() => handleRemoveProtocol(p.protocol_id)} className="text-red-600 hover:underline">
                      Rimuovi
                    </button>
                  )}
                </li>
              ))}
            </ul>
            {(!dossier.protocols || dossier.protocols.length === 0) && <p className="text-slate-500">Nessun protocollo collegato.</p>}
          </div>
        )}

        {tab === 'emails' && (
          <div>
            <ul className="space-y-2">
              {(dossier.dossier_emails ?? []).map((em: DossierEmailEntry) => (
                <li key={em.id} className="rounded border border-slate-200 px-3 py-2 text-sm">
                  <button
                    type="button"
                    className="flex w-full items-center justify-between text-left"
                    onClick={() => setEmailExpanded(emailExpanded === em.id ? null : em.id)}
                  >
                    <span className="font-medium">[{em.email_type}] {em.subject}</span>
                    <span className="text-slate-500">{new Date(em.received_at).toLocaleDateString('it-IT')}</span>
                  </button>
                  {emailExpanded === em.id && (
                    <div className="mt-2 border-t border-slate-100 pt-2 text-slate-600">
                      <p><strong>Da:</strong> {em.from_address}</p>
                      <p><strong>Oggetto:</strong> {em.subject}</p>
                      {em.body && <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">{em.body}</pre>}
                    </div>
                  )}
                </li>
              ))}
            </ul>
            {(!dossier.dossier_emails || dossier.dossier_emails.length === 0) && <p className="text-slate-500">Nessuna email/PEC.</p>}
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
