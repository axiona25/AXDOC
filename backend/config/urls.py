from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.authentication.views import sso_jwt_redirect_view, LDAPStatusView, LDAPSyncView
from apps.admin_panel.views import (
    LicenseView,
    SystemInfoView,
    BackupListView,
    BackupRunView,
    SettingsView,
    SettingsTestEmailView,
    SettingsTestLdapView,
)
from apps.admin_panel.health_views import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.authentication.urls")),
    path("api/auth/sso/jwt-redirect/", sso_jwt_redirect_view),
    path("api/auth/sso/", include("social_django.urls", namespace="social")),
    path("api/admin/ldap/status/", LDAPStatusView.as_view()),
    path("api/admin/ldap/sync/", LDAPSyncView.as_view()),
    path("api/admin/license/", LicenseView.as_view()),
    path("api/admin/settings/", SettingsView.as_view()),
    path("api/admin/settings/test_email/", SettingsTestEmailView.as_view()),
    path("api/admin/settings/test_ldap/", SettingsTestLdapView.as_view()),
    path("api/admin/system_info/", SystemInfoView.as_view()),
    path("api/admin/backups/", BackupListView.as_view()),
    path("api/admin/backups/run/", BackupRunView.as_view()),
    path("api/health/", HealthCheckView.as_view()),
    path("api/", include("apps.users.urls")),
    path("api/groups/", include("apps.users.groups_urls")),
    path("api/documents/", include("apps.documents.urls")),
    path("api/folders/", include("apps.documents.folders_urls")),
    path("api/metadata/", include("apps.metadata.urls")),
    path("api/protocols/", include("apps.protocols.urls")),
    path("api/workflows/", include("apps.workflows.urls")),
    path("api/dossiers/", include("apps.dossiers.urls")),
    path("api/", include("apps.signatures.urls")),
    path("api/sharing/", include("apps.sharing.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/search/", include("apps.search.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/chat/", include("apps.chat.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
    path("api/public/share/", include("apps.sharing.public_urls")),
    path("api/organizations/", include("apps.organizations.urls")),
    path("api/archive/", include("apps.archive.urls")),
    path("api/mail/", include("apps.mail.urls")),
    path("api/contacts/", include("apps.contacts.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
