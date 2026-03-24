import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  getFolders,
  getDocuments,
  createFolder,
  updateFolder,
  deleteFolder,
  uploadDocument,
  downloadDocument,
  copyDocument,
  moveDocument,
  deleteDocument,
  uploadDocumentVersion,
} from '../../services/documentService'
import { getMetadataStructures } from '../../services/metadataService'
import type { FolderItem, DocumentItem } from '../../services/documentService'
import type { MetadataStructure } from '../../types/metadata'
import { FolderTree } from './FolderTree'
import { DocumentTable } from './DocumentTable'
import { UploadModal } from './UploadModal'
import { DocumentDetailPanel } from './DocumentDetailPanel'
import { DocumentViewer } from '../viewer/DocumentViewer'

export function FileExplorer() {
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
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [viewerDocId, setViewerDocId] = useState<string | null>(null)
  const [visibilityFilter, setVisibilityFilter] = useState<'all' | 'personal' | 'office'>('all')

  const loadFolders = useCallback(() => {
    setLoadingFolders(true)
    getFolders({ all: 'true' })
      .then(setFolderTree)
      .finally(() => setLoadingFolders(false))
  }, [])

  useEffect(() => {
    if (uploadOpen) {
      getMetadataStructures({ applicable_to: 'document', usable_by_me: true })
        .then((r) => setMetadataStructures(r.results ?? []))
    }
  }, [uploadOpen])

  const loadDocuments = useCallback(() => {
    setLoadingDocs(true)
    getDocuments({
      folder_id: selectedFolderId ?? undefined,
      page: 1,
      ...(visibilityFilter !== 'all' && { visibility: visibilityFilter }),
    })
      .then((r) => setDocuments(r.results ?? []))
      .finally(() => setLoadingDocs(false))
  }, [selectedFolderId, visibilityFilter])

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
    setSearchParams(folder ? { folder: folder.id } : {})
  }

  const handleUpload = async (data: {
    title: string
    description: string
    folderId: string | null
    file: File
    metadataStructureId?: string | null
    metadataValues?: Record<string, unknown>
  }) => {
    const form = new FormData()
    form.append('title', data.title)
    form.append('description', data.description)
    if (data.folderId) form.append('folder_id', data.folderId)
    if (data.metadataStructureId) form.append('metadata_structure_id', data.metadataStructureId)
    if (data.metadataValues && Object.keys(data.metadataValues).length > 0) {
      form.append('metadata_values', JSON.stringify(data.metadataValues))
    }
    form.append('file', data.file)
    await uploadDocument(form, (p) => setUploadProgress(p))
    loadDocuments()
    loadFolders()
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
    })
  }

  const refreshDetail = () => {
    if (detailDoc) loadDocuments()
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

  return (
    <div className="flex h-full flex-col">
      <div className="flex w-full items-center gap-2 border-b border-slate-200 px-4 py-2">
        <button
          type="button"
          onClick={() => setUploadOpen(true)}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Carica documento
        </button>
        <button
          type="button"
          onClick={handleNewFolder}
          className="rounded bg-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-300"
        >
          Nuova cartella
        </button>
        <div className="ml-auto flex items-center gap-1 rounded border border-slate-200 bg-slate-50">
          {(['all', 'personal', 'office'] as const).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setVisibilityFilter(v)}
              className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                visibilityFilter === v
                  ? 'bg-indigo-600 text-white rounded'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {v === 'all' ? 'Tutti' : v === 'personal' ? 'Personali' : 'Ufficio'}
            </button>
          ))}
        </div>
      </div>
      <div className="flex min-h-0 flex-1">
        <div className="w-56 shrink-0 border-r border-slate-200 bg-slate-50 p-2">
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
          <div className="border-b border-slate-200 px-4 py-2 text-sm text-slate-600">
            {selectedFolderId ? `Cartella selezionata` : 'Root'}
          </div>
          <div className="flex-1 overflow-auto p-4">
            {loadingDocs ? (
              <p className="text-slate-500">Caricamento documenti...</p>
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
                selectedIds={selectedIds}
                onSelectionChange={setSelectedIds}
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
          <div className="flex h-full max-h-[90vh] w-full max-w-5xl flex-col rounded-lg bg-white shadow-xl overflow-hidden">
            <DocumentViewer documentId={viewerDocId} onClose={() => setViewerDocId(null)} showHeader />
          </div>
        </div>
      )}
      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={handleUpload}
        folders={flatFoldersForSelect(folderTree)}
        defaultFolderId={selectedFolderId}
        progress={uploadProgress}
        metadataStructures={metadataStructures}
      />
    </div>
  )
}
