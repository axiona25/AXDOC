interface TextViewerProps {
  content: string
  language?: string
  fileName?: string
  onDownload?: () => void
}

export function TextViewer({ content, language, fileName, onDownload }: TextViewerProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-end border-b border-slate-200 px-2 py-1.5 bg-slate-50">
        {onDownload && (
          <button type="button" onClick={onDownload} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white hover:bg-indigo-700">
            Scarica
          </button>
        )}
      </div>
      <div className="flex-1 overflow-auto p-4">
        <pre className="font-mono text-sm text-slate-800 whitespace-pre-wrap break-words bg-slate-50 rounded p-3" data-language={language} title={fileName || undefined}>
          <code>{content || '(vuoto)'}</code>
        </pre>
      </div>
    </div>
  )
}
