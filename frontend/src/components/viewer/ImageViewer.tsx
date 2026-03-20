import { useState, useRef } from 'react'

interface ImageViewerProps {
  url: string
  fileName?: string
  onDownload?: () => void
}

export function ImageViewer({ url, fileName, onDownload }: ImageViewerProps) {
  const [scale, setScale] = useState(1)
  const [fit, setFit] = useState<'none' | 'contain'>('contain')
  const containerRef = useRef<HTMLDivElement>(null)

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between gap-2 border-b border-slate-200 px-2 py-1.5 bg-slate-50">
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => setScale((s) => Math.max(0.25, s - 0.25))} className="rounded border border-slate-300 px-2 py-1 text-sm">
            −
          </button>
          <span className="text-sm text-slate-600">{Math.round(scale * 100)}%</span>
          <button type="button" onClick={() => setScale((s) => Math.min(4, s + 0.25))} className="rounded border border-slate-300 px-2 py-1 text-sm">
            +
          </button>
          <button
            type="button"
            onClick={() => setFit((f) => (f === 'contain' ? 'none' : 'contain'))}
            className="rounded border border-slate-300 px-2 py-1 text-sm"
          >
            {fit === 'contain' ? 'Adatta' : '100%'}
          </button>
        </div>
        {onDownload && (
          <button type="button" onClick={onDownload} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white hover:bg-indigo-700">
            Scarica
          </button>
        )}
      </div>
      <div
        ref={containerRef}
        className="flex-1 overflow-auto flex items-center justify-center p-4 bg-slate-100"
        style={{ minHeight: 200 }}
      >
        <img
          src={url}
          alt={fileName || 'Immagine'}
          className="max-w-full max-h-full object-contain transition-transform"
          style={{
            transform: `scale(${scale})`,
            objectFit: fit === 'contain' ? 'contain' : 'none',
          }}
          draggable={false}
        />
      </div>
    </div>
  )
}
