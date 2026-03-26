"""Test API admin panel (FASE 33) — copertura estesa views."""
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def admin_client(db):
    user = User.objects.create_user(
        email="admin-panel-f33@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="Admin",
        last_name="Panel",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def operator_client(db):
    user = User.objects.create_user(
        email="op-panel-f33@test.com",
        password="Op123456!",
        role="OPERATOR",
        first_name="Op",
        last_name="Panel",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestSettingsAPI:
    def test_get_settings_admin(self, admin_client):
        r = admin_client.get("/api/admin/settings/")
        assert r.status_code == 200
        assert "security" in r.data
        assert "email" in r.data

    def test_get_settings_operator_forbidden(self, operator_client):
        r = operator_client.get("/api/admin/settings/")
        assert r.status_code == 403

    def test_patch_organization_nested(self, admin_client):
        r = admin_client.patch(
            "/api/admin/settings/",
            {"organization": {"name": "Org F33", "code": "F33"}},
            format="json",
        )
        assert r.status_code == 200
        assert r.data.get("organization", {}).get("name") == "Org F33"

    def test_patch_security_password_policy(self, admin_client):
        r = admin_client.patch(
            "/api/admin/settings/",
            {
                "security": {
                    "password_min_length": 10,
                    "password_require_uppercase": True,
                    "login_attempts": 5,
                }
            },
            format="json",
        )
        assert r.status_code == 200
        sec = r.data.get("security") or {}
        assert sec.get("password_min_length") == 10

    def test_patch_ignores_non_dict_top_level(self, admin_client):
        r = admin_client.patch(
            "/api/admin/settings/",
            {"organization_name": "ignored", "email": {"backend_console": True}},
            format="json",
        )
        assert r.status_code == 200


@pytest.mark.django_db
class TestLicenseAPI:
    def test_get_license_admin(self, admin_client):
        r = admin_client.get("/api/admin/license/")
        assert r.status_code == 200
        assert "license" in r.data or "stats" in r.data

    def test_get_license_operator_forbidden(self, operator_client):
        r = operator_client.get("/api/admin/license/")
        assert r.status_code == 403


@pytest.mark.django_db
class TestSystemInfoAPI:
    def test_system_info_admin(self, admin_client):
        r = admin_client.get("/api/admin/system_info/")
        assert r.status_code == 200
        assert "django_version" in r.data

    def test_system_info_operator_forbidden(self, operator_client):
        r = operator_client.get("/api/admin/system_info/")
        assert r.status_code == 403


@pytest.mark.django_db
class TestBackupAPI:
    def test_backup_list_admin(self, admin_client):
        r = admin_client.get("/api/admin/backups/")
        assert r.status_code == 200
        assert "db" in r.data
        assert "media" in r.data

    def test_backup_list_operator_forbidden(self, operator_client):
        r = operator_client.get("/api/admin/backups/")
        assert r.status_code == 403

    @patch("django.core.management.call_command")
    def test_backup_run_admin(self, mock_cmd, admin_client):
        r = admin_client.post("/api/admin/backups/run/")
        assert r.status_code == 200
        assert r.data.get("status") == "completed"
        mock_cmd.assert_called_once()


@pytest.mark.django_db
class TestSettingsTestEmail:
    @patch("django.core.mail.send_mail")
    def test_test_email_ok(self, mock_send, admin_client):
        mock_send.return_value = 1
        r = admin_client.post("/api/admin/settings/test_email/", {"to": "a@b.com"}, format="json")
        assert r.status_code == 200
        assert r.data.get("status") == "ok"

    def test_test_email_operator_forbidden(self, operator_client):
        r = operator_client.post("/api/admin/settings/test_email/", {}, format="json")
        assert r.status_code == 403


@pytest.mark.django_db
class TestSettingsTestLdap:
    @patch("apps.admin_panel.views.SystemSettings.get_settings")
    def test_test_ldap_no_uri(self, mock_gs, admin_client):
        inst = MagicMock()
        inst.ldap = {}
        mock_gs.return_value = inst
        r = admin_client.post("/api/admin/settings/test_ldap/", {}, format="json")
        assert r.status_code == 400

    def test_test_ldap_operator_forbidden(self, operator_client):
        r = operator_client.post("/api/admin/settings/test_ldap/", {}, format="json")
        assert r.status_code == 403


@pytest.mark.django_db
class TestHealthCheck:
    def test_health_endpoint(self, client):
        r = client.get("/api/health/")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") in ("healthy", "degraded", "unhealthy")
