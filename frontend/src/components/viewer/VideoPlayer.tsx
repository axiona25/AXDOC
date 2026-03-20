interface VideoPlayerProps {
  url: string
  mimeType?: string
  fileName?: string
  onDownload?: () => void
}

export function VideoPlayer({ url, mimeType, fileName, onDownload }: VideoPlayerProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-end border-b border-slate-200 px-2 py-1.5 bg-slate-50">
        {onDownload && (
          <button type="button" onClick={onDownload} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white hover:bg-indigo-700">
            Scarica
          </button>
        )}
      </div>
      <div className="flex-1 flex items-center justify-center p-4 bg-black">
        <video
          src={url}
          controls
          className="max-w-full max-h-full"
          style={{ maxHeight: 'calc(100vh - 120px)' }}
          title={fileName || undefined}
          data-mime-type={mimeType || undefined}
        >
          Formato video non supportato. <a href={url} download>Scarica il file</a>
        </video>
      </div>
    </div>
  )
}
