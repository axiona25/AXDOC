import { PdfViewer } from './PdfViewer'

interface OfficeViewerProps {
  url: string
  fileName?: string
  originalFormat?: string
  onDownload?: () => void
}

export function OfficeViewer({ url, fileName, originalFormat, onDownload }: OfficeViewerProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 border-b border-slate-200 px-2 py-1.5 bg-amber-50 text-amber-800 text-sm">
        Convertito da {originalFormat || 'Office'} in PDF per l’anteprima.
      </div>
      <PdfViewer url={url} fileName={fileName} onDownload={onDownload} />
    </div>
  )
}
