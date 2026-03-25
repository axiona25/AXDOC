import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { logout } from '../services/authService'
import { getDashboardStats, getRecentDocuments, getMyTasks } from '../services/dashboardService'
import type { DashboardStats, RecentDocumentItem, MyTaskItem } from '../services/dashboardService'
import { GlobalSearchBar } from '../components/search/GlobalSearchBar'
import { NotificationBell } from '../components/notifications/NotificationBell'
import { ChatPanel } from '../components/chat/ChatPanel'
import { StatsCard } from '../components/dashboard/StatsCard'
import { DocumentsByStatusChart } from '../components/dashboard/DocumentsByStatusChart'
import { RecentActivityFeed } from '../components/dashboard/RecentActivityFeed'
import { PendingTasksWidget } from '../components/dashboard/PendingTasksWidget'
import { RecentDocumentsWidget } from '../components/dashboard/RecentDocumentsWidget'

export function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const [chatOpen, setChatOpen] = useState(false)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [recentDocs, setRecentDocs] = useState<{ results: RecentDocumentItem[] }>({ results: [] })
  const [myTasks, setMyTasks] = useState<{ results: MyTaskItem[] }>({ results: [] })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getDashboardStats().then(setStats).catch(() => setStats(null)),
      getRecentDocuments().then(setRecentDocs).catch(() => setRecentDocs({ results: [] })),
      getMyTasks().then(setMyTasks).catch(() => setMyTasks({ results: [] })),
    ]).finally(() => setLoading(false))
  }, [])

  const handleLogout = async () => {
    await logout()
    window.location.href = '/login'
  }

  const isAdmin = user?.role === 'ADMIN'
  const canArchive = user?.role === 'ADMIN' || user?.role === 'APPROVER'

  return (
    <div className="min-h-screen bg-slate-100 p-4 md:p-6">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white p-3 shadow md:mb-6 md:p-4">
        <h1 className="text-lg font-bold text-slate-800 md:text-xl">AXDOC — Dashboard</h1>
        <div className="flex flex-wrap items-center gap-2 md:gap-4">
          <GlobalSearchBar />
          <Link to="/search" className="text-sm text-indigo-600 hover:underline md:text-base">Ricerca</Link>
          <Link to="/documents" className="text-sm text-indigo-600 hover:underline md:text-base">Documenti</Link>
          <Link to="/tools/p7m-verify" className="text-sm text-indigo-600 hover:underline md:text-base">Verifica P7M</Link>
          <Link to="/workflows" className="text-sm text-indigo-600 hover:underline md:text-base">Workflow</Link>
          <Link to="/mail" className="text-sm text-indigo-600 hover:underline md:text-base">Posta</Link>
          <button
            type="button"
            onClick={() => setChatOpen((o) => !o)}
            className="rounded p-1.5 text-slate-600 hover:bg-slate-100"
            title="Chat"
          >
            💬
          </button>
          <NotificationBell />
          <Link to="/protocols" className="text-sm text-indigo-600 hover:underline md:text-base">Protocolli</Link>
          <Link to="/dossiers" className="text-sm text-indigo-600 hover:underline md:text-base">Fascicoli</Link>
          {canArchive && (
            <Link to="/archive" className="text-sm text-indigo-600 hover:underline md:text-base">Archivio</Link>
          )}
          {isAdmin && (
            <>
              <Link to="/metadata" className="text-sm text-indigo-600 hover:underline md:text-base">Metadati</Link>
              <Link to="/users" className="text-sm text-indigo-600 hover:underline md:text-base">Utenti</Link>
              <Link to="/organizations" className="text-sm text-indigo-600 hover:underline md:text-base">Organizzazioni</Link>
              <Link to="/settings" className="text-sm text-indigo-600 hover:underline md:text-base">Impostazioni</Link>
              <Link to="/admin/license" className="text-sm text-indigo-600 hover:underline md:text-base">Licenza</Link>
              <Link to="/audit" className="text-sm text-indigo-600 hover:underline md:text-base">Audit</Link>
            </>
          )}
          <Link to="/profile" className="text-sm text-indigo-600 hover:underline md:text-base">Profilo</Link>
          <span className="text-slate-600 text-sm md:text-base">
            {user?.first_name} {user?.last_name}
          </span>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded bg-slate-200 px-2 py-1 text-sm font-medium text-slate-700 hover:bg-slate-300 md:px-3 md:py-1.5"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="space-y-6">
        {loading ? (
          <p className="rounded-lg bg-white p-8 text-center text-slate-500 shadow">Caricamento...</p>
        ) : isAdmin ? (
          <>
            <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatsCard title="Utenti" value={stats?.total_users ?? 0} variant="blue" />
              <StatsCard title="Documenti" value={stats?.total_documents ?? 0} variant="green" />
              <StatsCard
                title="Fascicoli"
                value={((stats?.total_dossiers?.open ?? 0) + (stats?.total_dossiers?.archived ?? 0))}
                subtitle={`${stats?.total_dossiers?.open ?? 0} aperti`}
                variant="orange"
              />
              <StatsCard
                title="Protocolli"
                value={stats?.total_protocols?.count ?? 0}
                subtitle={stats?.total_protocols?.this_month != null ? `Questo mese: ${stats.total_protocols.this_month}` : undefined}
                variant="gray"
              />
            </section>
            <section className="grid gap-4 lg:grid-cols-2">
              <DocumentsByStatusChart documentsByStatus={stats?.documents_by_status} />
              <PendingTasksWidget tasks={myTasks.results} />
            </section>
            <section className="grid gap-4 lg:grid-cols-2">
              <RecentActivityFeed items={stats?.recent_activity ?? []} />
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
              />
              <StatsCard
                title="Step pendenti"
                value={stats?.my_pending_steps ?? 0}
                variant="orange"
              />
              <StatsCard
                title="Notifiche non lette"
                value={stats?.unread_notifications ?? 0}
                variant="gray"
              />
            </section>
            <section>
              <PendingTasksWidget tasks={myTasks.results} />
            </section>
            <section>
              <RecentDocumentsWidget
                documents={recentDocs.results}
                onSelectDocument={(id) => navigate(`/documents?doc=${id}`)}
              />
            </section>
          </>
        )}
      </main>
      <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
