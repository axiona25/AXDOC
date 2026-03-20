interface GenericViewerProps {
  fileName?: string
  fileSize?: number
  mimeType?: string
  onDownload?: () => void
}

export function GenericViewer({ fileName, fileSize, mimeType, onDownload }: GenericViewerProps) {
  const sizeStr = fileSize != null
    ? fileSize < 1024
      ? `${fileSize} B`
      : fileSize < 1024 * 1024
        ? `${(fileSize / 1024).toFixed(1)} KB`
        : `${(fileSize / (1024 * 1024)).toFixed(1)} MB`
    : '—'
  return (
    <div className="flex flex-col h-full items-center justify-center p-8 text-center">
      <div className="text-6xl text-slate-400 mb-4">📄</div>
      <p className="text-lg font-medium text-slate-700">{fileName || 'Documento'}</p>
      <p className="text-sm text-slate-500 mt-1">Dimensione: {sizeStr}</p>
      {mimeType && <p className="text-xs text-slate-400 mt-0.5">{mimeType}</p>}
      <p className="text-sm text-slate-600 mt-4">Anteprima non disponibile per questo formato.</p>
      {onDownload && (
        <button
          type="button"
          onClick={onDownload}
          className="mt-6 rounded bg-indigo-600 px-6 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Scarica
        </button>
      )}
    </div>
  )
}
