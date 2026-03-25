import { useState, useEffect, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { logout } from '../services/authService'
import {
  getDashboardStats,
  getRecentDocuments,
  getMyTasks,
  getDocumentsTrend,
  getProtocolsTrend,
  getWorkflowStats,
  getStorageTrend,
} from '../services/dashboardService'
import type {
  DashboardStats,
  RecentDocumentItem,
  MyTaskItem,
  MonthlyDataPoint,
  ProtocolTrendPoint,
  WorkflowStats,
  StorageTrendPoint,
} from '../services/dashboardService'
import { GlobalSearchBar } from '../components/search/GlobalSearchBar'
import { NotificationBell } from '../components/notifications/NotificationBell'
import { ChatPanel } from '../components/chat/ChatPanel'
import { StatsCard } from '../components/dashboard/StatsCard'
import { DocumentsByStatusChart } from '../components/dashboard/DocumentsByStatusChart'
import { DocumentsTrendChart } from '../components/dashboard/DocumentsTrendChart'
import { ProtocolsTrendChart } from '../components/dashboard/ProtocolsTrendChart'
import { WorkflowStatsWidget } from '../components/dashboard/WorkflowStatsWidget'
import { StorageTrendChart } from '../components/dashboard/StorageTrendChart'
import { RecentActivityFeed } from '../components/dashboard/RecentActivityFeed'
import { PendingTasksWidget } from '../components/dashboard/PendingTasksWidget'
import { RecentDocumentsWidget } from '../components/dashboard/RecentDocumentsWidget'
import { usePrefetchRoutes } from '../hooks/usePrefetchRoutes'

function trendFromMonthly(series: MonthlyDataPoint[]): {
  trend: 'up' | 'down' | 'flat'
  label: string
} | null {
  if (series.length < 2) return null
  const last = series[series.length - 1].count
  const prev = series[series.length - 2].count
  if (last === prev) return { trend: 'flat', label: 'vs mese prec.: stabile' }
  const pct = prev === 0 ? (last > 0 ? 100 : 0) : Math.round(((last - prev) / Math.max(prev, 1)) * 100)
  if (last > prev) return { trend: 'up', label: `vs mese prec.: +${pct}%` }
  return { trend: 'down', label: `vs mese prec.: ${pct}%` }
}

function aggregateProtocolsByMonth(results: ProtocolTrendPoint[]): MonthlyDataPoint[] {
  const m: Record<string, number> = {}
  for (const r of results) {
    m[r.month] = (m[r.month] || 0) + r.count
  }
  return Object.entries(m)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, count]) => ({ month, count }))
}

export function DashboardPage() {
  usePrefetchRoutes()
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const [chatOpen, setChatOpen] = useState(false)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [recentDocs, setRecentDocs] = useState<{ results: RecentDocumentItem[] }>({ results: [] })
  const [myTasks, setMyTasks] = useState<{ results: MyTaskItem[] }>({ results: [] })
  const [docTrend, setDocTrend] = useState<MonthlyDataPoint[]>([])
  const [protoTrend, setProtoTrend] = useState<ProtocolTrendPoint[]>([])
  const [workflowStats, setWorkflowStats] = useState<WorkflowStats | null>(null)
  const [storageTrend, setStorageTrend] = useState<StorageTrendPoint[]>([])
  const [loading, setLoading] = useState(true)

  const canWorkflowStats =
    user?.role === 'ADMIN' || user?.role === 'APPROVER' || user?.role === 'REVIEWER'

  useEffect(() => {
    const role = user?.role
    const wfAllowed = role === 'ADMIN' || role === 'APPROVER' || role === 'REVIEWER'
    const wf = wfAllowed ? getWorkflowStats().catch(() => null) : Promise.resolve(null)
    const st = role === 'ADMIN' ? getStorageTrend(12).catch(() => ({ results: [] })) : Promise.resolve({ results: [] })

    Promise.all([
      getDashboardStats().then(setStats).catch(() => setStats(null)),
      getRecentDocuments().then(setRecentDocs).catch(() => setRecentDocs({ results: [] })),
      getMyTasks().then(setMyTasks).catch(() => setMyTasks({ results: [] })),
      getDocumentsTrend(12).then((r) => setDocTrend(r.results)).catch(() => setDocTrend([])),
      getProtocolsTrend(12).then((r) => setProtoTrend(r.results)).catch(() => setProtoTrend([])),
      wf.then((w) => setWorkflowStats(w)),
      st.then((r) => setStorageTrend(r.results ?? [])),
    ]).finally(() => setLoading(false))
  }, [user?.role])

  const protoByMonth = useMemo(() => aggregateProtocolsByMonth(protoTrend), [protoTrend])
  const adminDocTrend = trendFromMonthly(docTrend)
  const adminProtoTrend = trendFromMonthly(protoByMonth)

  const myDocsByStatus = useMemo(() => {
    if (!stats?.my_documents) return null
    const m = stats.my_documents
    return {
      DRAFT: m.draft,
      IN_REVIEW: m.in_review,
      APPROVED: m.approved,
      REJECTED: m.rejected,
      ARCHIVED: m.archived,
    }
  }, [stats?.my_documents])

  const operatorDocTrend = trendFromMonthly(docTrend)

  const handleLogout = async () => {
    await logout()
    window.location.href = '/login'
  }

  const isAdmin = user?.role === 'ADMIN'
  const canArchive = user?.role === 'ADMIN' || user?.role === 'APPROVER'

  const navLink =
    'text-sm text-indigo-600 hover:underline dark:text-indigo-400 md:text-base'

  return (
    <div className="min-h-screen bg-slate-100 p-4 dark:bg-slate-900 md:p-6">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white p-3 shadow dark:border-slate-700 dark:bg-slate-800 md:mb-6 md:p-4">
        <h1 className="text-lg font-bold text-slate-800 dark:text-slate-100 md:text-xl">AXDOC — Dashboard</h1>
        <div className="flex flex-wrap items-center gap-2 md:gap-4">
          <GlobalSearchBar />
          <Link to="/search" className={navLink} onMouseEnter={() => void import('./SearchPage')}>
            Ricerca
          </Link>
          <Link to="/documents" className={navLink} onMouseEnter={() => void import('./DocumentsPage')}>
            Documenti
          </Link>
          <Link to="/tools/p7m-verify" className={navLink} onMouseEnter={() => void import('./P7MVerifyPage')}>
            Verifica P7M
          </Link>
          <Link to="/workflows" className={navLink} onMouseEnter={() => void import('./WorkflowBuilderPage')}>
            Workflow
          </Link>
          <Link to="/mail" className={navLink} onMouseEnter={() => void import('./MailPage')}>
            Posta
          </Link>
          <button
            type="button"
            onClick={() => setChatOpen((o) => !o)}
            className="rounded p-1.5 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
            title="Chat"
          >
            💬
          </button>
          <NotificationBell />
          <Link to="/protocols" className={navLink} onMouseEnter={() => void import('./ProtocolsPage')}>
            Protocolli
          </Link>
          <Link to="/dossiers" className={navLink} onMouseEnter={() => void import('./DossiersPage')}>
            Fascicoli
          </Link>
          {canArchive && (
            <Link to="/archive" className={navLink} onMouseEnter={() => void import('./ArchivePage')}>
              Archivio
            </Link>
          )}
          {isAdmin && (
            <>
              <Link to="/metadata" className={navLink} onMouseEnter={() => void import('./MetadataPage')}>
                Metadati
              </Link>
              <Link
                to="/document-templates"
                className={navLink}
                onMouseEnter={() => void import('./DocumentTemplatesPage')}
              >
                Template documenti
              </Link>
              <Link to="/users" className={navLink} onMouseEnter={() => void import('./UsersPage')}>
                Utenti
              </Link>
              <Link
                to="/organizations"
                className={navLink}
                onMouseEnter={() => void import('./OrganizationsPage')}
              >
                Organizzazioni
              </Link>
              <Link to="/settings" className={navLink} onMouseEnter={() => void import('./SettingsPage')}>
                Impostazioni
              </Link>
              <Link to="/admin/license" className={navLink} onMouseEnter={() => void import('./LicensePage')}>
                Licenza
              </Link>
              <Link to="/audit" className={navLink} onMouseEnter={() => void import('./AuditPage')}>
                Audit
              </Link>
              <Link
                to="/security-incidents"
                className={navLink}
                onMouseEnter={() => void import('./SecurityIncidentsPage')}
              >
                Incidenti sicurezza
              </Link>
            </>
          )}
          <Link to="/profile" className={navLink} onMouseEnter={() => void import('./ProfilePage')}>
            Profilo
          </Link>
          <span className="text-sm text-slate-600 dark:text-slate-300 md:text-base">
            {user?.first_name} {user?.last_name}
          </span>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded bg-slate-200 px-2 py-1 text-sm font-medium text-slate-700 hover:bg-slate-300 dark:bg-slate-600 dark:text-slate-100 dark:hover:bg-slate-500 md:px-3 md:py-1.5"
          >
            Logout
          </button>
        </div>
      </header>

      <div className="space-y-6">
        {loading ? (
          <p className="rounded-lg border border-slate-200 bg-white p-8 text-center text-slate-500 shadow dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
            Caricamento...
          </p>
        ) : isAdmin ? (
          <>
            <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatsCard title="Utenti" value={stats?.total_users ?? 0} variant="blue" />
              <StatsCard
                title="Documenti"
                value={stats?.total_documents ?? 0}
                variant="green"
                trend={adminDocTrend?.trend}
                trendLabel={adminDocTrend?.label}
              />
              <StatsCard
                title="Fascicoli"
                value={(stats?.total_dossiers?.open ?? 0) + (stats?.total_dossiers?.archived ?? 0)}
                subtitle={`${stats?.total_dossiers?.open ?? 0} aperti`}
                variant="orange"
              />
              <StatsCard
                title="Protocolli"
                value={stats?.total_protocols?.count ?? 0}
                subtitle={
                  stats?.total_protocols?.this_month != null
                    ? `Questo mese: ${stats.total_protocols.this_month}`
                    : undefined
                }
                variant="gray"
                trend={adminProtoTrend?.trend}
                trendLabel={adminProtoTrend?.label}
              />
            </section>

            <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <DocumentsTrendChart data={docTrend} />
              </div>
              <div className="lg:col-span-1">
                <DocumentsByStatusChart documentsByStatus={stats?.documents_by_status} />
              </div>
            </section>

            <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <ProtocolsTrendChart data={protoTrend} />
              </div>
              <div className="lg:col-span-1">
                {canWorkflowStats ? (
                  <WorkflowStatsWidget stats={workflowStats} />
                ) : (
                  <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
                    Statistiche workflow non disponibili per il tuo ruolo.
                  </div>
                )}
              </div>
            </section>

            <section>
              <StorageTrendChart data={storageTrend} />
            </section>

            <section>
              <RecentActivityFeed items={stats?.recent_activity ?? []} />
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <PendingTasksWidget tasks={myTasks.results} />
              <RecentDocumentsWidget
                documents={recentDocs.results}
                onSelectDocument={(id) => navigate(`/documents?doc=${id}`)}
              />
            </section>
          </>
        ) : (
          <>
            <section className="grid gap-4 sm:grid-cols-3">
              <StatsCard
                title="I miei documenti"
                value={stats?.my_documents?.total ?? 0}
                variant="blue"
                trend={operatorDocTrend?.trend}
                trendLabel={operatorDocTrend?.label}
              />
              <StatsCard title="Step pendenti" value={stats?.my_pending_steps ?? 0} variant="orange" />
              <StatsCard title="Notifiche non lette" value={stats?.unread_notifications ?? 0} variant="gray" />
            </section>

            <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <DocumentsTrendChart data={docTrend} />
              </div>
              <div className="lg:col-span-1">
                <DocumentsByStatusChart documentsByStatus={myDocsByStatus} />
              </div>
            </section>

            <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <ProtocolsTrendChart data={protoTrend} />
              </div>
              <div className="lg:col-span-1">
                {canWorkflowStats ? (
                  <WorkflowStatsWidget stats={workflowStats} />
                ) : (
                  <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
                    I dettagli workflow sono riservati ad approvatori e revisori.
                  </div>
                )}
              </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <PendingTasksWidget tasks={myTasks.results} />
              <RecentDocumentsWidget
                documents={recentDocs.results}
                onSelectDocument={(id) => navigate(`/documents?doc=${id}`)}
              />
            </section>
          </>
        )}
      </div>
      <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
