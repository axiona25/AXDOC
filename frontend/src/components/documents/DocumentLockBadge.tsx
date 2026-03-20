interface DocumentLockBadgeProps {
  lockedBy: { id: string; email?: string; first_name?: string; last_name?: string } | null
  isCurrentUser: boolean
  onUnlock?: () => void
  unlocking?: boolean
}

export function DocumentLockBadge({
  lockedBy,
  isCurrentUser,
  onUnlock,
  unlocking,
}: DocumentLockBadgeProps) {
  if (!lockedBy) return null

  const name = [lockedBy.first_name, lockedBy.last_name].filter(Boolean).join(' ') || lockedBy.email || 'Utente'

  return (
    <div className="flex items-center gap-2 rounded bg-amber-100 px-2 py-1 text-sm text-amber-800">
      <span>🔒 Bloccato da {name}</span>
      {isCurrentUser && onUnlock && (
        <button
          type="button"
          onClick={onUnlock}
          disabled={unlocking}
          className="rounded bg-amber-200 px-2 py-0.5 text-xs font-medium hover:bg-amber-300 disabled:opacity-50"
        >
          {unlocking ? 'Sblocco...' : 'Sblocca'}
        </button>
      )}
    </div>
  )
}
