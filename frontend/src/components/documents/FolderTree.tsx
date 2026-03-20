import { useState } from 'react'
import type { FolderItem } from '../../services/documentService'

interface FolderTreeProps {
  folders: FolderItem[]
  selectedId: string | null
  onSelect: (folder: FolderItem | null) => void
  onRename?: (folder: FolderItem) => void
  onDelete?: (folder: FolderItem) => void
  onNewSubfolder?: (parent: FolderItem) => void
  loading?: boolean
}

export function FolderTree({
  folders,
  selectedId,
  onSelect,
  onRename,
  onDelete,
  onNewSubfolder,
  loading,
}: FolderTreeProps) {
  return (
    <div className="min-h-0 flex-1 overflow-auto">
      {loading && (
        <div className="py-2 text-sm text-slate-500">Caricamento...</div>
      )}
      <ul className="list-none pl-0">
        <li>
          <button
            type="button"
            onClick={() => onSelect(null)}
            className={`w-full rounded px-2 py-1.5 text-left text-sm font-medium ${selectedId === null ? 'bg-indigo-100 text-indigo-800' : 'text-slate-700 hover:bg-slate-100'}`}
          >
            📁 Root
          </button>
        </li>
        {folders.map((f) => (
          <FolderTreeNode
            key={f.id}
            folder={f}
            selectedId={selectedId}
            onSelect={onSelect}
            onRename={onRename}
            onDelete={onDelete}
            onNewSubfolder={onNewSubfolder}
            level={0}
          />
        ))}
      </ul>
    </div>
  )
}

function FolderTreeNode({
  folder,
  selectedId,
  onSelect,
  onRename,
  onDelete,
  onNewSubfolder,
  level,
}: {
  folder: FolderItem
  selectedId: string | null
  onSelect: (folder: FolderItem | null) => void
  onRename?: (folder: FolderItem) => void
  onDelete?: (folder: FolderItem) => void
  onNewSubfolder?: (parent: FolderItem) => void
  level: number
}) {
  const [expanded, setExpanded] = useState(true)
  const [contextMenu, setContextMenu] = useState(false)
  const subfolders = folder.subfolders ?? []
  const hasChildren = subfolders.length > 0
  const isSelected = selectedId === folder.id

  return (
    <li className="py-0.5">
      <div
        className="group flex items-center gap-1 rounded px-2 py-1.5 hover:bg-slate-100"
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onContextMenu={(e) => {
          e.preventDefault()
          setContextMenu(true)
        }}
      >
        <button
          type="button"
          onClick={() => setExpanded((x) => !x)}
          className="shrink-0 p-0.5 text-slate-500"
          aria-label={expanded ? 'Chiudi' : 'Espandi'}
        >
          {hasChildren ? (expanded ? '▼' : '▶') : ' '}
        </button>
        <button
          type="button"
          onClick={() => onSelect(folder)}
          className={`min-w-0 flex-1 truncate text-left text-sm ${isSelected ? 'font-semibold text-indigo-700' : 'text-slate-700'}`}
        >
          📁 {folder.name}
        </button>
      </div>
      {contextMenu && (
        <>
          <div
            className="fixed inset-0 z-10"
            role="button"
            tabIndex={0}
            onClick={() => setContextMenu(false)}
            onKeyDown={(e) => e.key === 'Escape' && setContextMenu(false)}
            aria-label="Chiudi menu"
          />
          <div
            className="z-20 rounded border border-slate-200 bg-white py-1 shadow-lg"
            style={{ marginLeft: `${level * 12 + 24}px` }}
          >
            {onRename && (
              <button
                type="button"
                className="block w-full px-3 py-1.5 text-left text-sm hover:bg-slate-100"
                onClick={() => { onRename(folder); setContextMenu(false) }}
              >
                Rinomina
              </button>
            )}
            {onNewSubfolder && (
              <button
                type="button"
                className="block w-full px-3 py-1.5 text-left text-sm hover:bg-slate-100"
                onClick={() => { onNewSubfolder(folder); setContextMenu(false) }}
              >
                Nuova sottocartella
              </button>
            )}
            {onDelete && (
              <button
                type="button"
                className="block w-full px-3 py-1.5 text-left text-sm text-red-600 hover:bg-red-50"
                onClick={() => { onDelete(folder); setContextMenu(false) }}
              >
                Elimina
              </button>
            )}
          </div>
        </>
      )}
      {expanded && hasChildren && (
        <ul className="list-none pl-0">
          {subfolders.map((child) => (
            <FolderTreeNode
              key={child.id}
              folder={child}
              selectedId={selectedId}
              onSelect={onSelect}
              onRename={onRename}
              onDelete={onDelete}
              onNewSubfolder={onNewSubfolder}
              level={level + 1}
            />
          ))}
        </ul>
      )}
    </li>
  )
}
