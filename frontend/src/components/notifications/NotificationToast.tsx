import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, GitBranch, PenTool, Share2, type LucideIcon, X } from 'lucide-react'
import {
  requestOpenNotificationsPanel,
  type ToastNotification,
  useToastStore,
} from '../../store/toastStore'

const DISMISS_MS = 5000

function iconForType(notificationType: string): LucideIcon {
  const t = notificationType || ''
  if (t.startsWith('workflow_')) return GitBranch
  if (t.startsWith('signature_')) return PenTool
  if (t.startsWith('share_') || t === 'document_shared') return Share2
  return Bell
}

export interface NotificationToastContainerProps {
  toasts: ToastNotification[]
  onDismiss: (id: string) => void
  onNavigate: (linkUrl: string) => void
}

export function NotificationToastContainer({
  toasts,
  onDismiss,
  onNavigate,
}: NotificationToastContainerProps) {
  const ordered = [...toasts].reverse()

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="false"
      aria-relevant="additions"
      className="pointer-events-none fixed inset-x-0 bottom-4 z-[100] flex flex-col items-stretch gap-2 px-4 md:inset-x-auto md:bottom-auto md:right-4 md:top-4 md:items-end md:px-0"
    >
      {ordered.map((toast) => (
        <NotificationToastItem
          key={toast.id}
          toast={toast}
          onDismiss={() => onDismiss(toast.id)}
          onNavigate={onNavigate}
        />
      ))}
    </div>
  )
}

interface NotificationToastItemProps {
  toast: ToastNotification
  onDismiss: () => void
  onNavigate: (linkUrl: string) => void
}

export function NotificationToastItem({ toast, onDismiss, onNavigate }: NotificationToastItemProps) {
  const [phase, setPhase] = useState<'enter' | 'shown' | 'exit'>('enter')
  const deadlineRef = useRef(0)
  const remainingRef = useRef(DISMISS_MS)
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>()
  const dismissedRef = useRef(false)

  const clearTimer = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = undefined
    }
  }, [])

  const startExit = useCallback(() => {
    clearTimer()
    setPhase((p) => (p === 'exit' ? p : 'exit'))
  }, [clearTimer])

  const schedule = useCallback(() => {
    clearTimer()
    const ms = deadlineRef.current - Date.now()
    if (ms <= 0) {
      startExit()
      return
    }
    timeoutRef.current = setTimeout(startExit, ms)
  }, [clearTimer, startExit])

  useEffect(() => {
    dismissedRef.current = false
    const id = requestAnimationFrame(() => setPhase('shown'))
    return () => cancelAnimationFrame(id)
  }, [toast.id])

  useEffect(() => {
    if (phase !== 'shown') return
    deadlineRef.current = Date.now() + DISMISS_MS
    remainingRef.current = DISMISS_MS
    schedule()
    return () => clearTimer()
  }, [phase, schedule, clearTimer])

  const onMouseEnter = () => {
    if (phase !== 'shown') return
    clearTimer()
    remainingRef.current = Math.max(0, deadlineRef.current - Date.now())
  }

  const onMouseLeave = () => {
    if (phase !== 'shown') return
    deadlineRef.current = Date.now() + remainingRef.current
    schedule()
  }

  const handleTransitionEnd = (e: React.TransitionEvent<HTMLDivElement>) => {
    if (e.propertyName !== 'transform' && e.propertyName !== 'opacity') return
    if (e.target !== e.currentTarget) return
    if (phase !== 'exit' || dismissedRef.current) return
    dismissedRef.current = true
    onDismiss()
  }

  const handleActivate = () => {
    const link = toast.link_url?.trim() ?? ''
    if (link) {
      onNavigate(link)
    } else {
      requestOpenNotificationsPanel()
    }
    startExit()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleActivate()
    }
  }

  const Icon = iconForType(toast.notification_type)

  const surface =
    phase === 'enter'
      ? 'translate-x-full opacity-0'
      : phase === 'exit'
        ? 'translate-x-full opacity-0'
        : 'translate-x-0 opacity-100'

  return (
    <div
      className={`group pointer-events-auto w-full max-w-full cursor-pointer rounded-lg border border-slate-200 bg-white shadow-lg transition-all duration-300 ease-out dark:border-slate-600 dark:bg-slate-800 md:max-w-sm ${surface}`}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onTransitionEnd={handleTransitionEnd}
    >
      <div
        className="flex gap-3 p-3 pr-2"
        onClick={handleActivate}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        aria-label={`Notifica: ${toast.title}`}
      >
        <Icon className="mt-0.5 h-5 w-5 shrink-0 text-indigo-600 dark:text-indigo-400" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{toast.title}</p>
          <p className="mt-0.5 line-clamp-2 text-xs leading-snug text-slate-600 dark:text-slate-300">{toast.message}</p>
        </div>
        <button
          type="button"
          className="shrink-0 rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-200"
          aria-label="Chiudi notifica"
          onClick={(e) => {
            e.stopPropagation()
            startExit()
          }}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      {phase === 'shown' && (
        <div className="h-1 w-full overflow-hidden rounded-b bg-slate-100 dark:bg-slate-700">
          <div
            className="h-full origin-left bg-indigo-500 group-hover:[animation-play-state:paused] dark:bg-indigo-400"
            style={{
              animation: `axdoc-toast-progress ${DISMISS_MS}ms linear forwards`,
            }}
          />
        </div>
      )}
    </div>
  )
}

export function NotificationToastHost() {
  const navigate = useNavigate()
  const toasts = useToastStore((s) => s.toasts)
  const removeToast = useToastStore((s) => s.removeToast)

  const onNavigate = useCallback(
    (linkUrl: string) => {
      const path = linkUrl.startsWith('/') ? linkUrl : `/${linkUrl}`
      navigate(path)
    },
    [navigate],
  )

  if (toasts.length === 0) return null

  return (
    <NotificationToastContainer toasts={toasts} onDismiss={removeToast} onNavigate={onNavigate} />
  )
}
