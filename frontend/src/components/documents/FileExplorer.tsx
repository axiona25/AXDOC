import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { FileSpreadsheet, Trash2, FolderInput, Archive } from 'lucide-react'
import {
  getFolders,
  getDocuments,
  createFolder,
  updateFolder,
  deleteFolder,
  uploadDocument,
  getDocument,
  downloadDocument,
  copyDocument,
  moveDocument,
  deleteDocument,
  uploadDocumentVersion,
  bulkDeleteDocuments,
  bulkMoveDocuments,
  bulkStatusDocuments,
  startDocumentWorkflow,
} from '../../services/documentService'
import { getMetadataStructures } from '../../services/metadataService'
import { getUsers } from '../../services/userService'
import type { FolderItem, DocumentItem } from '../../services/documentService'
import type { MetadataStructure } from '../../types/metadata'
import { FolderTree } from './FolderTree'
import { DocumentTable } from './DocumentTable'
import { UploadModal } from './UploadModal'
import { DocumentDetailPanel } from './DocumentDetailPanel'
import { DocumentViewer } from '../viewer/DocumentViewer'
import { exportDocumentsExcel } from '../../services/exportService'
import { FilterPanel, type FilterField } from '../common/FilterPanel'
import { BulkActionBar } from '../common/BulkActionBar'
import { useBulkSelection } from '../../hooks/useBulkSelection'
import { useAuthStore } from '../../store/authStore'
import { ConfirmModal } from '../common/ConfirmModal'
import { announce } from '../common/ScreenReaderAnnouncer'

export function FileExplorer() {
  const user = useAuthStore((s) => s.user)
  const canBulkStatus = user?.role === 'ADMIN' || user?.role === 'APPROVER'
  const [searchParams, setSearchParams] = useSearchParams()
  const folderIdFromUrl = searchParams.get('folder')
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(folderIdFromUrl)
  const [folderTree, setFolderTree] = useState<FolderItem[]>([])
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [loadingFolders, setLoadingFolders] = useState(true)
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [detailDoc, setDetailDoc] = useState<DocumentItem | null>(null)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [metadataStructures, setMetadataStructures] = useState<MetadataStructure[]>([])
  const [viewerDocId, setViewerDocId] = useState<string | null>(null)
  const [visibilityFilter, setVisibilityFilter] = useState<'all' | 'personal' | 'office'>('all')
  const [userOptions, setUserOptions] = useState<{ value: string; label: string }[]>([])
  const [moveOpen, setMoveOpen] = useState(false)
  const [bulkTargetFolder, setBulkTargetFolder] = useState<string>('')
  const [rootConfirmOpen, setRootConfirmOpen] = useState(false)

  const bulk = useBulkSelection<string>()

  const filterFields = useMemo<FilterField[]>(() => {
    const statusOpts = [
      { value: 'DRAFT', label: 'Bozza' },
      { value: 'IN_REVIEW', label: 'In revisione' },
      { value: 'APPROVED', label: 'Approvato' },
      { value: 'REJECTED', label: 'Rifiutato' },
      { value: 'ARCHIVED', label: 'Archiviato' },
    ]
    const metaOpts = metadataStructures.map((m) => ({ value: m.id, label: m.name }))
    return [
      { name: 'status', label: 'Stato', type: 'select', options: statusOpts },
      { name: 'date_from', label: 'Data da', type: 'date' },
      { name: 'date_to', label: 'Data a', type: 'date' },
      { name: 'created_by', label: 'Creato da', type: 'select', options: userOptions },
      { name: 'metadata_structure_id', label: 'Struttura metadati', type: 'select', options: metaOpts },
    ]
  }, [metadataStructures, userOptions])

  const loadFolders = useCallback(() => {
    setLoadingFolders(true)
    getFolders({ all: 'true' })
      .then(setFolderTree)
      .finally(() => setLoadingFolders(false))
  }, [])

  useEffect(() => {
    getMetadataStructures({ applicable_to: 'document', usable_by_me: true })
      .then((r) => setMetadataStructures(r.results ?? []))
      .catch(() => setMetadataStructures([]))
    getUsers({ page: 1 })
      .then((r) =>
        setUserOptions(
          (r.results ?? []).map((u) => ({
            value: u.id,
            label: `${u.first_name ?? ''} ${u.last_name ?? ''} (${u.email})`.trim() || u.email,
          })),
        ),
      )
      .catch(() => setUserOptions([]))
  }, [])

  useEffect(() => {
    if (uploadOpen) {
      getMetadataStructures({ applicable_to: 'document', usable_by_me: true })
        .then((r) => setMetadataStructures(r.results ?? []))
    }
  }, [uploadOpen])

  const statusQ = searchParams.get('status') ?? ''
  const dateFromQ = searchParams.get('date_from') ?? ''
  const dateToQ = searchParams.get('date_to') ?? ''
  const createdByQ = searchParams.get('created_by') ?? ''
  const metaIdQ = searchParams.get('metadata_structure_id') ?? ''

  const loadDocuments = useCallback(() => {
    setLoadingDocs(true)
    getDocuments({
      folder_id: selectedFolderId ?? undefined,
      page: 1,
      ...(visibilityFilter !== 'all' && { visibility: visibilityFilter }),
      ...(statusQ && { status: statusQ }),
      ...(dateFromQ && { date_from: dateFromQ }),
      ...(dateToQ && { date_to: dateToQ }),
      ...(createdByQ && { created_by: createdByQ }),
      ...(metaIdQ && { metadata_structure_id: metaIdQ }),
    })
      .then((r) => setDocuments(r.results ?? []))
      .finally(() => setLoadingDocs(false))
  }, [
    selectedFolderId,
    visibilityFilter,
    statusQ,
    dateFromQ,
    dateToQ,
    createdByQ,
    metaIdQ,
  ])

  useEffect(() => {
    setSelectedFolderId(folderIdFromUrl)
  }, [folderIdFromUrl])

  useEffect(() => {
    loadFolders()
  }, [loadFolders])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  const handleSelectFolder = (folder: FolderItem | null) => {
    setSelectedFolderId(folder?.id ?? null)
    const next = new URLSearchParams(searchParams)
    if (folder) next.set('folder', folder.id)
    else next.delete('folder')
    setSearchParams(next, { replace: true })
  }

  const handleUpload = async (data: {
    title: string
    description: string
    folderId: string | null
    file: File
    metadataStructureId?: string | null
    metadataValues?: Record<string, unknown>
    visibility?: 'personal' | 'office'
    templateMeta?: { auto_start_workflow: boolean; workflowTemplateId: string | null } | null
  }) => {
    const form = new FormData()
    form.append('title', data.title)
    form.append('description', data.description)
    if (data.folderId) form.append('folder_id', data.folderId)
    if (data.metadataStructureId) form.append('metadata_structure_id', data.metadataStructureId)
    if (data.metadataValues && Object.keys(data.metadataValues).length > 0) {
      form.append('metadata_values', JSON.stringify(data.metadataValues))
    }
    if (data.visibility) form.append('visibility', data.visibility)
    form.append('file', data.file)
    const doc = await uploadDocument(form, (p) => setUploadProgress(p))
    if (data.templateMeta?.auto_start_workflow && data.templateMeta.workflowTemplateId) {
      try {
        await startDocumentWorkflow(doc.id, data.templateMeta.workflowTemplateId)
      } catch {
        /* workflow opzionale */
      }
    }
    loadDocuments()
    loadFolders()
  }

  const runBulkDelete = async () => {
    if (bulk.ids.length === 0) return
    const n = bulk.ids.length
    await bulkDeleteDocuments(bulk.ids)
    bulk.deselectAll()
    loadDocuments()
    setDetailDoc(null)
    announce(`${n} documenti eliminati`)
  }

  const runBulkMove = async (folderId: string | null) => {
    if (bulk.ids.length === 0) return
    const n = bulk.ids.length
    await bulkMoveDocuments(bulk.ids, folderId)
    bulk.deselectAll()
    setMoveOpen(false)
    loadDocuments()
    announce(`${n} documenti spostati`)
  }

  const runBulkArchive = async () => {
    if (bulk.ids.length === 0) return
    const n = bulk.ids.length
    await bulkStatusDocuments(bulk.ids, 'ARCHIVED')
    bulk.deselectAll()
    loadDocuments()
    announce(`${n} documenti archiviati`)
  }

  const handleNewFolder = () => {
    const name = window.prompt('Nome cartella')
    if (!name?.trim()) return
    createFolder({ name: name.trim(), parent_id: selectedFolderId }).then(() => {
      loadFolders()
    })
  }

  const handleRenameFolder = (folder: FolderItem) => {
    const name = window.prompt('Nuovo nome', folder.name)
    if (!name?.trim()) return
    updateFolder(folder.id, { name: name.trim(), parent_id: folder.parent_id }).then(loadFolders)
  }

  const handleDeleteFolder = (folder: FolderItem) => {
    if (!window.confirm(`Eliminare la cartella "${folder.name}"?`)) return
    deleteFolder(folder.id).then(() => {
      loadFolders()
      if (selectedFolderId === folder.id) handleSelectFolder(null)
    })
  }

  const handleNewSubfolder = (parent: FolderItem) => {
    const name = window.prompt('Nome sottocartella')
    if (!name?.trim()) return
    createFolder({ name: name.trim(), parent_id: parent.id }).then(() => {
      loadFolders()
    })
  }

  const handleDownload = (doc: DocumentItem) => {
    downloadDocument(doc.id)
  }

  const handleNewVersion = (doc: DocumentItem) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.onchange = () => {
      const file = input.files?.[0]
      if (!file) return
      const form = new FormData()
      form.append('file', file)
      uploadDocumentVersion(doc.id, form)
        .then(() => {
          loadDocuments()
          if (detailDoc?.id === doc.id) setDetailDoc({ ...detailDoc, current_version: detailDoc.current_version + 1 })
        })
    }
    input.click()
  }

  const handleCopy = (doc: DocumentItem) => {
    copyDocument(doc.id, { new_title: `${doc.title} (copia)` }).then(() => loadDocuments())
  }

  const handleMove = (doc: DocumentItem) => {
    const targetId = window.prompt('ID cartella di destinazione (lascia vuoto per root)', '')
    moveDocument(doc.id, targetId?.trim() || null).then(() => {
      loadDocuments()
      if (detailDoc?.id === doc.id) setDetailDoc(null)
    })
  }

  const handleDeleteDoc = (doc: DocumentItem) => {
    if (!window.confirm(`Eliminare "${doc.title}"?`)) return
    deleteDocument(doc.id).then(() => {
      loadDocuments()
      if (detailDoc?.id === doc.id) setDetailDoc(null)
      announce('Documento eliminato')
    })
  }

  const refreshDetail = () => {
    loadDocuments()
    if (detailDoc) {
      getDocument(detailDoc.id)
        .then(setDetailDoc)
        .catch(() => {})
    }
  }

  const flatFoldersForSelect = (list: FolderItem[]): FolderItem[] => {
    const out: FolderItem[] = []
    const visit = (items: FolderItem[]) => {
      items.forEach((f) => {
        out.push(f)
        if (f.subfolders?.length) visit(f.subfolders)
      })
    }
    visit(list)
    return out
  }

  const flatFolders = flatFoldersForSelect(folderTree)

  const exportParams = {
    folder_id: selectedFolderId ?? undefined,
    ...(statusQ && { status: statusQ }),
    ...(dateFromQ && { date_from: dateFromQ }),
    ...(dateToQ && { date_to: dateToQ }),
    ...(createdByQ && { created_by: createdByQ }),
    ...(metaIdQ && { metadata_structure_id: metaIdQ }),
    ...(visibilityFilter !== 'all' && { visibility: visibilityFilter }),
  }

  return (
    <div className="flex h-full flex-col bg-white dark:bg-slate-800">
      <div className="border-b border-slate-200 px-4 py-2 dark:border-slate-700">
        <FilterPanel fields={filterFields} onApply={() => loadDocuments()} onReset={() => loadDocuments()} />
      </div>
      <div className="flex w-full items-center gap-2 border-b border-slate-200 px-4 py-2 dark:border-slate-700">
        <button
          type="button"
          onClick={() => setUploadOpen(true)}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 dark:hover:bg-indigo-500"
        >
          Carica documento
        </button>
        <button
          type="button"
          onClick={handleNewFolder}
          className="rounded bg-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
        >
          Nuova cartella
        </button>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => exportDocumentsExcel(exportParams)}
            className="flex items-center gap-1.5 rounded bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
          >
            <FileSpreadsheet className="h-4 w-4" aria-hidden />
            Esporta Excel
          </button>
          <div className="flex items-center gap-1 rounded border border-slate-200 bg-slate-50 dark:border-slate-600 dark:bg-slate-700/50">
            {(['all', 'personal', 'office'] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setVisibilityFilter(v)}
                className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                  visibilityFilter === v
                    ? 'rounded bg-indigo-600 text-white'
                    : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-600'
                }`}
              >
                {v === 'all' ? 'Tutti' : v === 'personal' ? 'Personali' : 'Ufficio'}
              </button>
            ))}
          </div>
        </div>
      </div>
      <BulkActionBar
        count={bulk.count}
        onDeselectAll={bulk.deselectAll}
        actions={[
          {
            label: 'Elimina',
            icon: <Trash2 className="h-4 w-4" />,
            variant: 'danger',
            requireConfirm: true,
            confirmTitle: 'Eliminare i documenti?',
            confirmMessage: `Verranno eliminati ${bulk.count} documenti (soft delete).`,
            onClick: runBulkDelete,
          },
          {
            label: 'Sposta in cartella',
            icon: <FolderInput className="h-4 w-4" />,
            onClick: () => {
              setBulkTargetFolder('')
              setMoveOpen(true)
            },
          },
          ...(canBulkStatus
            ? [
                {
                  label: 'Archivia',
                  icon: <Archive className="h-4 w-4" />,
                  requireConfirm: true,
                  confirmTitle: 'Archiviare?',
                  confirmMessage: `Archiviare ${bulk.count} documenti?`,
                  onClick: runBulkArchive,
                },
              ]
            : []),
        ]}
      />
      <div className="flex min-h-0 flex-1">
        <div className="w-56 shrink-0 border-r border-slate-200 bg-slate-50 p-2 dark:border-slate-700 dark:bg-slate-900/40">
          <FolderTree
            folders={folderTree}
            selectedId={selectedFolderId}
            onSelect={handleSelectFolder}
            onRename={handleRenameFolder}
            onDelete={handleDeleteFolder}
            onNewSubfolder={handleNewSubfolder}
            loading={loadingFolders}
          />
        </div>
        <div className="min-w-0 flex-1 flex flex-col">
          <div className="border-b border-slate-200 px-4 py-2 text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">
            {selectedFolderId ? `Cartella selezionata` : 'Root'}
          </div>
          <div className="flex-1 overflow-auto p-4">
            {loadingDocs ? (
              <p className="text-slate-500 dark:text-slate-400">Caricamento documenti...</p>
            ) : (
              <DocumentTable
                documents={documents}
                onOpen={setDetailDoc}
                onView={(doc) => setViewerDocId(doc.id)}
                onDownload={handleDownload}
                onNewVersion={handleNewVersion}
                onCopy={handleCopy}
                onMove={handleMove}
                onDelete={handleDeleteDoc}
                selectedIds={bulk.selectedIds}
                onSelectionChange={bulk.setSelection}
              />
            )}
          </div>
        </div>
        {detailDoc && (
          <div className="w-[480px] shrink-0">
            <DocumentDetailPanel
              document={detailDoc}
              onClose={() => setDetailDoc(null)}
              onRefresh={refreshDetail}
              onNewVersion={handleNewVersion}
              onVisualize={() => setViewerDocId(detailDoc.id)}
            />
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
      {moveOpen && (
        <div className="fixed inset-0 z-[55] flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-4 shadow-xl dark:border-slate-600 dark:bg-slate-800">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">Sposta documenti</h3>
            <select
              value={bulkTargetFolder}
              onChange={(e) => setBulkTargetFolder(e.target.value)}
              className="mt-3 w-full rounded border border-slate-300 bg-white px-2 py-2 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100"
            >
              <option value="">— Root —</option>
              {flatFolders.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setMoveOpen(false)}
                className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-500 dark:text-slate-200"
              >
                Annulla
              </button>
              <button
                type="button"
                onClick={() => {
                  if (bulkTargetFolder) runBulkMove(bulkTargetFolder)
                  else setRootConfirmOpen(true)
                }}
                className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white dark:hover:bg-indigo-500"
              >
                Sposta
              </button>
            </div>
          </div>
        </div>
      )}
      <ConfirmModal
        open={rootConfirmOpen}
        title="Spostare in root?"
        message="Confermi lo spostamento nella cartella principale (nessuna cartella)?"
        onConfirm={() => {
          setRootConfirmOpen(false)
          runBulkMove(null)
        }}
        onCancel={() => setRootConfirmOpen(false)}
      />
      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={handleUpload}
        folders={flatFolders}
        defaultFolderId={selectedFolderId}
        progress={uploadProgress}
        metadataStructures={metadataStructures}
      />
    </div>
  )
}
