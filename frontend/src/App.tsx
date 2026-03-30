import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { ChangePasswordModal } from './components/auth/ChangePasswordModal'
import { LoginPage } from './pages/LoginPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { AcceptInvitationPage } from './pages/AcceptInvitationPage'
import { SSOCallbackPage } from './pages/SSOCallbackPage'
import { UnauthorizedPage } from './pages/UnauthorizedPage'
import { PublicSharePage } from './pages/PublicSharePage'
import { NotificationToastHost } from './components/notifications/NotificationToast'
import { NotificationWsProvider } from './components/notifications/NotificationWsContext'
import { PageLoader } from './components/layout/PageLoader'
import { SkipLink } from './components/layout/SkipLink'
import { ScreenReaderAnnouncer } from './components/common/ScreenReaderAnnouncer'

const ChangePasswordPage = lazy(() =>
  import('./pages/ChangePasswordPage').then((m) => ({ default: m.ChangePasswordPage })),
)
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
)
const UsersPage = lazy(() => import('./pages/UsersPage').then((m) => ({ default: m.UsersPage })))
const OrganizationsPage = lazy(() =>
  import('./pages/OrganizationsPage').then((m) => ({ default: m.OrganizationsPage })),
)
const GroupsPage = lazy(() => import('./pages/GroupsPage').then((m) => ({ default: m.GroupsPage })))
const GroupDetailPage = lazy(() =>
  import('./pages/GroupDetailPage').then((m) => ({ default: m.GroupDetailPage })),
)
const LicensePage = lazy(() =>
  import('./pages/LicensePage').then((m) => ({ default: m.LicensePage })),
)
const SettingsPage = lazy(() =>
  import('./pages/SettingsPage').then((m) => ({ default: m.SettingsPage })),
)
const ProfilePage = lazy(() =>
  import('./pages/ProfilePage').then((m) => ({ default: m.ProfilePage })),
)
const DocumentsPage = lazy(() =>
  import('./pages/DocumentsPage').then((m) => ({ default: m.DocumentsPage })),
)
const P7MVerifyPage = lazy(() =>
  import('./pages/P7MVerifyPage').then((m) => ({ default: m.P7MVerifyPage })),
)
const WorkflowBuilderPage = lazy(() =>
  import('./pages/WorkflowBuilderPage').then((m) => ({ default: m.WorkflowBuilderPage })),
)
const MetadataPage = lazy(() =>
  import('./pages/MetadataPage').then((m) => ({ default: m.MetadataPage })),
)
const DocumentTemplatesPage = lazy(() =>
  import('./pages/DocumentTemplatesPage').then((m) => ({ default: m.DocumentTemplatesPage })),
)
const ProtocolsPage = lazy(() =>
  import('./pages/ProtocolsPage').then((m) => ({ default: m.ProtocolsPage })),
)
const ProtocolDetailPage = lazy(() =>
  import('./pages/ProtocolDetailPage').then((m) => ({ default: m.ProtocolDetailPage })),
)
const DailyRegisterPage = lazy(() =>
  import('./pages/DailyRegisterPage').then((m) => ({ default: m.DailyRegisterPage })),
)
const DossiersPage = lazy(() =>
  import('./pages/DossiersPage').then((m) => ({ default: m.DossiersPage })),
)
const DossierDetailPage = lazy(() =>
  import('./pages/DossierDetailPage').then((m) => ({ default: m.DossierDetailPage })),
)
const SearchPage = lazy(() => import('./pages/SearchPage').then((m) => ({ default: m.SearchPage })))
const ContactDetailPage = lazy(() =>
  import('./pages/ContactDetailPage').then((m) => ({ default: m.ContactDetailPage })),
)
const AuditPage = lazy(() => import('./pages/AuditPage').then((m) => ({ default: m.AuditPage })))
const ArchivePage = lazy(() =>
  import('./pages/ArchivePage').then((m) => ({ default: m.ArchivePage })),
)
const MailPage = lazy(() => import('./pages/MailPage').then((m) => ({ default: m.MailPage })))
const PrivacyConsentPage = lazy(() =>
  import('./pages/PrivacyConsentPage').then((m) => ({ default: m.PrivacyConsentPage })),
)
const SecurityIncidentsPage = lazy(() =>
  import('./pages/SecurityIncidentsPage').then((m) => ({ default: m.SecurityIncidentsPage })),
)

function App() {
  const initializeAuth = useAuthStore((s) => s.initializeAuth)
  const user = useAuthStore((s) => s.user)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const refetchUser = useAuthStore((s) => s.initializeAuth)

  useEffect(() => {
    initializeAuth()
  }, [initializeAuth])

  const showChangePasswordModal =
    isAuthenticated && user && user.must_change_password === true

  return (
    <>
      <SkipLink />
      <ScreenReaderAnnouncer />
      <BrowserRouter>
      <NotificationWsProvider>
        {showChangePasswordModal && (
          <ChangePasswordModal
            isOpen={true}
            onSuccess={async () => {
              await refetchUser()
            }}
          />
        )}
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
            <Route
              path="/change-password"
              element={
                <ProtectedRoute>
                  <ChangePasswordPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/documents"
              element={
                <ProtectedRoute>
                  <DocumentsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/tools/p7m-verify"
              element={
                <ProtectedRoute>
                  <P7MVerifyPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/workflows"
              element={
                <ProtectedRoute>
                  <WorkflowBuilderPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/metadata"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <MetadataPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/document-templates"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <DocumentTemplatesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/protocols"
              element={
                <ProtectedRoute>
                  <ProtocolsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/mail"
              element={
                <ProtectedRoute>
                  <MailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/protocols/registro-giornaliero"
              element={
                <ProtectedRoute>
                  <DailyRegisterPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/protocols/:id"
              element={
                <ProtectedRoute>
                  <ProtocolDetailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dossiers"
              element={
                <ProtectedRoute>
                  <DossiersPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dossiers/:id"
              element={
                <ProtectedRoute>
                  <DossierDetailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/users"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <UsersPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/organizations"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <OrganizationsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/groups"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <GroupsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/groups/:id"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <GroupDetailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/license"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <LicensePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <SettingsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <ProfilePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/privacy"
              element={
                <ProtectedRoute>
                  <PrivacyConsentPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/security-incidents"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <SecurityIncidentsPage />
                </ProtectedRoute>
              }
            />
            <Route path="/accept-invitation/:token" element={<AcceptInvitationPage />} />
            <Route path="/sso-callback" element={<SSOCallbackPage />} />
            <Route path="/unauthorized" element={<UnauthorizedPage />} />
            <Route path="/share/:token" element={<PublicSharePage />} />
            <Route
              path="/search"
              element={
                <ProtectedRoute>
                  <SearchPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/contacts/:id"
              element={
                <ProtectedRoute>
                  <ContactDetailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/audit"
              element={
                <ProtectedRoute>
                  <AuditPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/archive"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'APPROVER']}>
                  <ArchivePage />
                </ProtectedRoute>
              }
            />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
        <NotificationToastHost />
      </NotificationWsProvider>
      </BrowserRouter>
    </>
  )
}

export default App
