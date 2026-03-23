import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { ChangePasswordModal } from './components/auth/ChangePasswordModal'
import { LoginPage } from './pages/LoginPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { ChangePasswordPage } from './pages/ChangePasswordPage'
import { DashboardPage } from './pages/DashboardPage'
import { UsersPage } from './pages/UsersPage'
import { OrganizationsPage } from './pages/OrganizationsPage'
import { GroupsPage } from './pages/GroupsPage'
import { GroupDetailPage } from './pages/GroupDetailPage'
import { LicensePage } from './pages/LicensePage'
import { SettingsPage } from './pages/SettingsPage'
import { ProfilePage } from './pages/ProfilePage'
import { DocumentsPage } from './pages/DocumentsPage'
import { MetadataPage } from './pages/MetadataPage'
import { ProtocolsPage } from './pages/ProtocolsPage'
import { ProtocolDetailPage } from './pages/ProtocolDetailPage'
import { DailyRegisterPage } from './pages/DailyRegisterPage'
import { DossiersPage } from './pages/DossiersPage'
import { DossierDetailPage } from './pages/DossierDetailPage'
import { AcceptInvitationPage } from './pages/AcceptInvitationPage'
import { SSOCallbackPage } from './pages/SSOCallbackPage'
import { UnauthorizedPage } from './pages/UnauthorizedPage'
import { PublicSharePage } from './pages/PublicSharePage'
import { SearchPage } from './pages/SearchPage'
import { AuditPage } from './pages/AuditPage'
import { ArchivePage } from './pages/ArchivePage'
import { MailPage } from './pages/MailPage'
import './index.css'

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
    <BrowserRouter>
      {showChangePasswordModal && (
        <ChangePasswordModal
          isOpen={true}
          onSuccess={async () => {
            await refetchUser()
          }}
        />
      )}
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
          path="/metadata"
          element={
            <ProtectedRoute allowedRoles={['ADMIN']}>
              <MetadataPage />
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
    </BrowserRouter>
  )
}

export default App
