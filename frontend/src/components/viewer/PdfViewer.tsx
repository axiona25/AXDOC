import { useState } from 'react'
import { Document, Page } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

interface PdfViewerProps {
  url: string
  fileName?: string
  onDownload?: () => void
}

export function PdfViewer({ url, fileName, onDownload }: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number | null>(null)
  const [pageNumber, setPageNumber] = useState(1)
  const [scale, setScale] = useState(1.0)

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between gap-2 border-b border-slate-200 px-2 py-1.5 bg-slate-50">
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={pageNumber <= 1}
            onClick={() => setPageNumber((p) => Math.max(1, p - 1))}
            className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-50"
          >
            ←
          </button>
          <span className="text-sm text-slate-600">
            Pagina {pageNumber} {numPages != null ? ` di ${numPages}` : ''}
          </span>
          <button
            type="button"
            disabled={numPages != null && pageNumber >= numPages}
            onClick={() => setPageNumber((p) => Math.min(numPages ?? p, p + 1))}
            className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-50"
          >
            →
          </button>
          <button type="button" onClick={() => setScale((s) => Math.max(0.5, s - 0.25))} className="rounded border border-slate-300 px-2 py-1 text-sm">
            −
          </button>
          <span className="text-sm text-slate-600">{Math.round(scale * 100)}%</span>
          <button type="button" onClick={() => setScale((s) => Math.min(2, s + 0.25))} className="rounded border border-slate-300 px-2 py-1 text-sm">
            +
          </button>
        </div>
        {onDownload && (
          <button type="button" onClick={onDownload} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white hover:bg-indigo-700" title={fileName ? `Scarica ${fileName}` : 'Scarica'}>
            Scarica
          </button>
        )}
      </div>
      <div className="flex-1 overflow-auto flex justify-center p-4">
        <Document
          file={url}
          onLoadSuccess={({ numPages: n }) => setNumPages(n)}
          loading={<div className="py-8 text-slate-500">Caricamento PDF...</div>}
          error={<div className="py-8 text-red-600">Errore caricamento PDF.</div>}
        >
          <Page pageNumber={pageNumber} scale={scale} renderTextLayer />
        </Document>
      </div>
    </div>
  )
}
