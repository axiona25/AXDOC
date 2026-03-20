interface EmailViewerProps {
  data: { from?: string; to?: string; subject?: string; date?: string; body_text?: string; body_html?: string; attachments?: Array<{ filename?: string; content_type?: string; size?: number }> }
  onDownload?: () => void
}

export function EmailViewer({ data, onDownload }: EmailViewerProps) {
  const hasHtml = data.body_html && data.body_html.trim().length > 0
  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-end border-b border-slate-200 px-2 py-1.5 bg-slate-50">
        {onDownload && (
          <button type="button" onClick={onDownload} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white hover:bg-indigo-700">
            Scarica
          </button>
        )}
      </div>
      <div className="flex-1 overflow-auto p-4 space-y-4">
        <div className="rounded border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm"><span className="font-medium text-slate-500">Da:</span> {data.from || '—'}</p>
          <p className="text-sm"><span className="font-medium text-slate-500">A:</span> {data.to || '—'}</p>
          <p className="text-sm"><span className="font-medium text-slate-500">Oggetto:</span> {data.subject || '—'}</p>
          <p className="text-sm"><span className="font-medium text-slate-500">Data:</span> {data.date || '—'}</p>
        </div>
        {data.attachments && data.attachments.length > 0 && (
          <div>
            <p className="text-sm font-medium text-slate-600 mb-1">Allegati</p>
            <ul className="list-disc list-inside text-sm text-slate-700">
              {data.attachments.map((a, i) => (
                <li key={i}>{a.filename || 'File'} ({a.size != null ? `${(a.size / 1024).toFixed(1)} KB` : '—'})</li>
              ))}
            </ul>
          </div>
        )}
        <div className="rounded border border-slate-200 bg-slate-50 p-4">
          {hasHtml ? (
            <iframe
              srcDoc={data.body_html}
              title="Corpo email"
              className="w-full min-h-[200px] border-0 rounded"
              sandbox="allow-same-origin"
            />
          ) : (
            <pre className="font-mono text-sm text-slate-800 whitespace-pre-wrap">{data.body_text || '(nessun contenuto)'}</pre>
          )}
        </div>
      </div>
    </div>
  )
}
