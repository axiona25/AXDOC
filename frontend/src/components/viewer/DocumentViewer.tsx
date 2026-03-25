import { useState, useEffect, useRef } from 'react'
import {
  getViewerInfo,
  getPreviewBlobUrl,
  getPreviewJson,
  downloadDocument,
  getDownloadBlobUrl,
} from '../../services/documentService'
import type { ViewerInfo } from '../../services/documentService'
import { PdfViewer } from './PdfViewer'
import { OfficeViewer } from './OfficeViewer'
import { ImageViewer } from './ImageViewer'
import { VideoPlayer } from './VideoPlayer'
import { AudioPlayer } from './AudioPlayer'
import { EmailViewer } from './EmailViewer'
import { TextViewer } from './TextViewer'
import { GenericViewer } from './GenericViewer'
import { P7MViewer } from './P7MViewer'

interface DocumentViewerProps {
  documentId: string
  versionNumber?: number
  onClose?: () => void
  /** Se true, mostra header con nome file, scarica, chiudi. */
  showHeader?: boolean
}

export function DocumentViewer({ documentId, onClose, showHeader = true, versionNumber }: DocumentViewerProps) {
  const [info, setInfo] = useState<ViewerInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [emailData, setEmailData] = useState<Record<string, unknown> | null>(null)
  const [textData, setTextData] = useState<{ content?: string; language?: string } | null>(null)
  const blobUrlRef = useRef<string | null>(null)

  useEffect(() => {
    let cancelled = false
    if (blobUrlRef.current && typeof URL.revokeObjectURL === 'function') {
      URL.revokeObjectURL(blobUrlRef.current)
      blobUrlRef.current = null
    }
    setBlobUrl(null)
    setEmailData(null)
    setTextData(null)
    setError(null)
    setInfo(null)
    setLoading(true)

    getViewerInfo(documentId)
      .then((i: ViewerInfo) => {
        if (cancelled) return
        setInfo(i)
        const vt = i.viewer_type
        const isP7m = (i.file_name || '').toLowerCase().endsWith('.p7m')
        if (vt === 'email') {
          return getPreviewJson<Record<string, unknown>>(documentId).then((d: Record<string, unknown>) => {
            if (!cancelled) setEmailData(d)
          })
        }
        if (vt === 'text') {
          return getPreviewJson<{ content?: string; language?: string }>(documentId).then((d: { content?: string; language?: string }) => {
            if (!cancelled) setTextData(d)
          })
        }
        if (vt === 'generic' && !isP7m) return Promise.resolve()
        if (vt === 'generic' && isP7m) {
          return getDownloadBlobUrl(documentId, versionNumber).then((url: string) => {
            if (!cancelled) {
              blobUrlRef.current = url
              setBlobUrl(url)
            } else if (typeof URL.revokeObjectURL === 'function') {
              URL.revokeObjectURL(url)
            }
          })
        }
        return getPreviewBlobUrl(documentId).then(({ url }: { url: string }) => {
          if (!cancelled) {
            blobUrlRef.current = url
            setBlobUrl(url)
          } else if (typeof URL.revokeObjectURL === 'function') {
            URL.revokeObjectURL(url)
          }
        })
      })
      .catch((e: unknown) => { if (!cancelled) setError((e as Error)?.message || 'Errore caricamento') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => {
      cancelled = true
      if (blobUrlRef.current && typeof URL.revokeObjectURL === 'function') {
        URL.revokeObjectURL(blobUrlRef.current)
        blobUrlRef.current = null
      }
    }
  }, [documentId, versionNumber])

  const handleDownload = () => {
    downloadDocument(documentId)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 text-slate-500">
        Caricamento...
      </div>
    )
  }
  if (error || !info) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-red-600">
        <p>{error || 'Impossibile caricare il documento.'}</p>
        {onClose && (
          <button type="button" onClick={onClose} className="mt-4 rounded bg-slate-200 px-4 py-2 text-sm text-slate-700">
            Chiudi
          </button>
        )}
      </div>
    )
  }

  const { viewer_type: viewerType, file_name: fileName, file_size: fileSize, mime_type: mimeType } = info

  return (
    <div className="flex flex-col h-full min-h-0">
      {showHeader && (
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2 bg-white shrink-0">
          <div className="min-w-0 truncate">
            <p className="font-medium text-slate-800 truncate">{fileName}</p>
            <p className="text-xs text-slate-500">{mimeType} · {(fileSize / 1024).toFixed(1)} KB</p>
          </div>
          <div className="flex gap-2 shrink-0">
            <button type="button" onClick={handleDownload} className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-300">
              Scarica
            </button>
            {onClose && (
              <button type="button" onClick={onClose} className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-300">
                Chiudi
              </button>
            )}
          </div>
        </div>
      )}
      <div className="flex-1 min-h-0 overflow-hidden">
        {viewerType === 'pdf' && blobUrl && (
          <PdfViewer url={blobUrl} fileName={fileName} />
        )}
        {viewerType === 'office' && blobUrl && (
          <OfficeViewer url={blobUrl} fileName={fileName} originalFormat={mimeType} onDownload={handleDownload} />
        )}
        {viewerType === 'image' && blobUrl && (
          <ImageViewer url={blobUrl} fileName={fileName} onDownload={handleDownload} />
        )}
        {viewerType === 'video' && blobUrl && (
          <VideoPlayer url={blobUrl} mimeType={mimeType} fileName={fileName} onDownload={handleDownload} />
        )}
        {viewerType === 'audio' && blobUrl && (
          <AudioPlayer url={blobUrl} fileName={fileName} onDownload={handleDownload} />
        )}
        {viewerType === 'email' && emailData && (
          <EmailViewer data={emailData as Parameters<typeof EmailViewer>[0]['data']} onDownload={handleDownload} />
        )}
        {viewerType === 'text' && textData && (
          <TextViewer content={textData.content || ''} language={textData.language} fileName={fileName} onDownload={handleDownload} />
        )}
        {fileName?.toLowerCase().endsWith('.p7m') && blobUrl && (
          <P7MViewer url={blobUrl} fileName={fileName} onDownload={handleDownload} />
        )}
        {viewerType === 'generic' && !fileName?.toLowerCase().endsWith('.p7m') && (
          <GenericViewer fileName={fileName} fileSize={fileSize} mimeType={mimeType} onDownload={handleDownload} />
        )}
      </div>
    </div>
  )
}
