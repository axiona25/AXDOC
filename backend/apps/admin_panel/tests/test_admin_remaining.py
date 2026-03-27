"""Copertura residua admin_panel.views (FASE 33D)."""
import sys
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.admin_panel.models import SystemLicense
from apps.admin_panel.views import _list_backup_files

User = get_user_model()


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(
        email="adm-rem@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="R",
    )
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.django_db
class TestLicenseWithRecord:
    def test_license_with_active_license(self, admin_client, db):
        today = timezone.now().date()
        SystemLicense.objects.update_or_create(
            pk=1,
            defaults={
                "organization_name": "Org X",
                "activated_at": today,
                "expires_at": today.replace(year=today.year + 1),
                "max_users": 100,
                "max_storage_gb": 50.0,
                "features_enabled": {"mfa": True},
            },
        )
        r = admin_client.get("/api/admin/license/")
        assert r.status_code == 200
        assert r.data.get("license") is not None
        assert r.data["license"]["organization_name"] == "Org X"

    @patch("apps.documents.models.DocumentVersion.objects.count", side_effect=RuntimeError("db"))
    def test_license_stats_documents_count_exception(self, _mock_count, admin_client, db):
        today = timezone.now().date()
        SystemLicense.objects.update_or_create(
            pk=1,
            defaults={
                "organization_name": "Org Ex",
                "activated_at": today,
                "expires_at": None,
                "max_users": None,
                "max_storage_gb": None,
                "features_enabled": {},
            },
        )
        r = admin_client.get("/api/admin/license/")
        assert r.status_code == 200
        assert r.data["stats"].get("documents_count") == 0


@pytest.mark.django_db
class TestSettingsPatchAllSections:
    def test_patch_email_storage_ldap_conservation_protocol(self, admin_client):
        r = admin_client.patch(
            "/api/admin/settings/",
            {
                "email": {"backend_console": True},
                "storage": {"max_upload_mb": 20},
                "ldap": {"server_uri": "ldap://test", "bind_dn": "cn=admin", "password": "x"},
                "conservation": {"enabled": True},
                "protocol": {"prefix": "PROT"},
            },
            format="json",
        )
        assert r.status_code == 200
        assert r.data["email"].get("backend_console") is True
        assert r.data["storage"].get("max_upload_mb") == 20


@pytest.mark.django_db
class TestSystemInfoBranches:
    @patch("redis.from_url")
    def test_system_info_redis_connected(self, mock_from_url, admin_client):
        mock_r = MagicMock()
        mock_r.ping.return_value = True
        mock_from_url.return_value = mock_r
        r = admin_client.get("/api/admin/system_info/")
        assert r.status_code == 200
        assert r.data.get("redis_connected") is True

    def test_system_info_ldap_branch(self, admin_client):
        conn = MagicMock()
        ldap_mod = MagicMock()
        ldap_mod.initialize = MagicMock(return_value=conn)
        with patch.dict(sys.modules, {"ldap": ldap_mod}):
            with override_settings(
                LDAP_ENABLED=True,
                AUTH_LDAP_SERVER_URI="ldap://localhost",
                AUTH_LDAP_BIND_DN="",
                AUTH_LDAP_BIND_PASSWORD="",
            ):
                r = admin_client.get("/api/admin/system_info/")
        assert r.status_code == 200
        assert r.data.get("ldap_connected") is True
        conn.simple_bind_s.assert_called_once()
        conn.unbind_s.assert_called_once()


@pytest.mark.django_db
class TestSettingsTestLdapSuccess:
    @patch("apps.admin_panel.views.SystemSettings.get_settings")
    def test_test_ldap_ok(self, mock_gs, admin_client):
        inst = MagicMock()
        inst.ldap = {"server_uri": "ldap://localhost", "bind_dn": "cn=x", "password": "y"}
        mock_gs.return_value = inst
        conn = MagicMock()
        ldap_mod = MagicMock()
        ldap_mod.initialize = MagicMock(return_value=conn)
        with patch.dict(sys.modules, {"ldap": ldap_mod}):
            r = admin_client.post("/api/admin/settings/test_ldap/", {}, format="json")
        assert r.status_code == 200
        assert r.data.get("status") == "ok"


@pytest.mark.django_db
class TestSettingsTestEmailErrors:
    @patch("django.core.mail.send_mail")
    def test_test_email_missing_to_and_user_without_email(self, mock_send, db):
        u = User(email="tmp-empty-mail@test.com", role="ADMIN", first_name="N", last_name="E")
        u.set_password("x")
        u.save()
        User.objects.filter(pk=u.pk).update(email="")
        u.refresh_from_db()
        c = APIClient()
        c.force_authenticate(user=u)
        r = c.post("/api/admin/settings/test_email/", {}, format="json")
        assert r.status_code == 400

    @patch("django.core.mail.send_mail")
    def test_test_email_send_failure(self, mock_send, admin_client):
        mock_send.side_effect = OSError("smtp down")
        r = admin_client.post("/api/admin/settings/test_email/", {"to": "a@b.com"}, format="json")
        assert r.status_code == 500


@pytest.mark.django_db
class TestBackupRunError:
    @patch("django.core.management.call_command")
    def test_backup_run_returns_500_on_error(self, mock_cmd, admin_client):
        mock_cmd.side_effect = RuntimeError("backup failed")
        r = admin_client.post("/api/admin/backups/run/")
        assert r.status_code == 500
        assert r.data.get("status") == "error"

    @patch("django.core.management.call_command")
    @patch("apps.admin_panel.views._list_backup_files")
    def test_backup_run_uses_stdout(self, mock_list, mock_cmd, admin_client):
        mock_cmd.side_effect = lambda *a, **kw: kw["stdout"].write("done")
        mock_list.return_value = [{"filename": "db.dump", "size_bytes": 1, "date": "x", "type": "db"}]
        r = admin_client.post("/api/admin/backups/run/")
        assert r.status_code == 200


@pytest.mark.django_db
class TestBackupListWithFiles:
    def test_backup_list_finds_dump_and_media(self, admin_client, tmp_path):
        dbdir = tmp_path / "db"
        dbdir.mkdir()
        (dbdir / "snap.dump").write_bytes(b"x")
        (dbdir / "ignored.txt").write_bytes(b"z")
        (dbdir / "notfile.dump").mkdir()
        media = tmp_path / "media"
        media.mkdir()
        (media / "files.tar.gz").write_bytes(b"y")
        with override_settings(DBBACKUP_STORAGE_OPTIONS={"location": str(dbdir)}):
            r = admin_client.get("/api/admin/backups/")
        assert r.status_code == 200
        db_names = [x.get("filename") for x in r.data.get("db", [])]
        assert any("snap.dump" in (n or "") for n in db_names)
        assert not any("ignored.txt" in (n or "") for n in db_names)
        assert not any("notfile.dump" in (n or "") for n in db_names)
        assert any("files.tar.gz" in (x.get("filename") or "") for x in r.data.get("media", []))


def test_list_backup_files_empty_dir(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    assert _list_backup_files(str(d), ".dump", "db", limit=5) == []


def test_list_backup_files_nonexistent():
    assert _list_backup_files("/nonexistent-path-axdoc-33d", ".dump", "db") == []


def test_list_backup_files_oserror_on_stat(tmp_path, monkeypatch):
    d = tmp_path / "st"
    d.mkdir()
    (d / "bad.dump").write_bytes(b"x")
    monkeypatch.setattr(
        "apps.admin_panel.views.os.path.getsize",
        lambda _p: (_ for _ in ()).throw(OSError("no stat")),
    )
    out = _list_backup_files(str(d), ".dump", "db", limit=5)
    assert len(out) == 1
    assert out[0].get("error") == "inaccessible"


@pytest.mark.django_db
class TestSettingsTestLdapBindFailure:
    @patch("apps.admin_panel.views.SystemSettings.get_settings")
    def test_test_ldap_exception_returns_400(self, mock_gs, admin_client):
        inst = MagicMock()
        inst.ldap = {"server_uri": "ldap://localhost", "bind_dn": "cn=x", "password": "y"}
        mock_gs.return_value = inst
        conn = MagicMock()
        conn.simple_bind_s.side_effect = Exception("bind failed")
        ldap_mod = MagicMock()
        ldap_mod.initialize = MagicMock(return_value=conn)
        with patch.dict(sys.modules, {"ldap": ldap_mod}):
            r = admin_client.post("/api/admin/settings/test_ldap/", {}, format="json")
        assert r.status_code == 400
        assert "bind failed" in (r.data.get("detail") or "")


@pytest.mark.django_db
class TestSystemInfoFailures:
    def test_redis_ping_failure(self, admin_client):
        import redis

        with patch.object(redis, "from_url", side_effect=OSError("redis down")):
            r = admin_client.get("/api/admin/system_info/")
        assert r.status_code == 200
        assert r.data.get("redis_connected") is False

    def test_ldap_connect_failure_when_enabled(self, admin_client):
        ldap_mod = MagicMock()
        ldap_mod.initialize.side_effect = Exception("ldap init fail")
        with patch.dict(sys.modules, {"ldap": ldap_mod}):
            with override_settings(
                LDAP_ENABLED=True,
                AUTH_LDAP_SERVER_URI="ldap://localhost",
                AUTH_LDAP_BIND_DN="",
                AUTH_LDAP_BIND_PASSWORD="",
            ):
                r = admin_client.get("/api/admin/system_info/")
        assert r.status_code == 200
        assert r.data.get("ldap_connected") is False
