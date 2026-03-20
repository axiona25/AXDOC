interface AudioPlayerProps {
  url: string
  fileName?: string
  onDownload?: () => void
}

export function AudioPlayer({ url, fileName, onDownload }: AudioPlayerProps) {
  return (
    <div className="flex flex-col h-full p-4">
      <div className="flex items-center justify-between gap-2 mb-4">
        <span className="text-sm font-medium text-slate-700 truncate">{fileName || 'Audio'}</span>
        {onDownload && (
          <button type="button" onClick={onDownload} className="rounded bg-indigo-600 px-3 py-1 text-sm text-white hover:bg-indigo-700 shrink-0">
            Scarica
          </button>
        )}
      </div>
      <audio src={url} controls className="w-full" />
    </div>
  )
}
