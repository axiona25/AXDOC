# FASE 34 — Copertura preview() in documents/views.py (righe ~615-832)
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import FieldFile
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentVersion, Folder
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="Prv OU", code="PRV", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="prv100-adm@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="P",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="Prv F", tenant=tenant, created_by=admin_user)


def _doc_with_version(admin_user, folder, file_name, content, ctype, ftype="application/pdf"):
    doc = Document.objects.create(
        title="Preview doc",
        tenant=folder.tenant,
        folder=folder,
        created_by=admin_user,
        owner=admin_user,
        current_version=1,
    )
    v = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        file_name=file_name,
        file_type=ftype,
        is_current=True,
        created_by=admin_user,
    )
    v.file.save(file_name, SimpleUploadedFile(file_name, content, content_type=ctype), save=True)
    return doc


@pytest.mark.django_db
class TestDocumentPreviewBranches:
    def test_preview_email(self, admin_client, admin_user, folder):
        from unittest.mock import patch

        doc = _doc_with_version(admin_user, folder, "m.eml", b"From: x\n\nHi", "message/rfc822", "message/rfc822")
        with patch("apps.documents.viewer.get_viewer_type", return_value="email"):
            with patch("apps.documents.viewer.parse_eml", return_value={"from": "a", "subject": "s"}):
                r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200
        assert r["X-Viewer-Type"] == "email"

    def test_preview_text_json_lang(self, admin_client, admin_user, folder):
        from unittest.mock import patch

        doc = _doc_with_version(admin_user, folder, "x.json", b'{"a":1}', "application/json", "application/json")
        with patch("apps.documents.viewer.get_viewer_type", return_value="text"):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200
        assert r.json().get("language") == "json"

    def test_preview_generic(self, admin_client, admin_user, folder):
        from unittest.mock import patch

        doc = _doc_with_version(admin_user, folder, "x.bin", b"abc", "application/octet-stream", "application/octet-stream")
        with patch("apps.documents.viewer.get_viewer_type", return_value="generic"):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 415

    def test_preview_pdf(self, admin_client, admin_user, folder):
        doc = _doc_with_version(admin_user, folder, "a.pdf", b"%PDF-1.4", "application/pdf", "application/pdf")
        r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200
        assert r["X-Viewer-Type"] == "pdf"

    def test_preview_image_inline(self, admin_client, admin_user, folder):
        doc = _doc_with_version(admin_user, folder, "p.png", b"\x89PNG\r\n\x1a\n", "image/png", "image/png")
        r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200

    def test_preview_no_file_404(self, admin_client, admin_user, folder):
        doc = Document.objects.create(
            title="No file",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            file_type="application/pdf",
            is_current=True,
            created_by=admin_user,
        )
        r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 404

    def test_preview_pdf_open_error(self, admin_client, admin_user, folder, monkeypatch):
        doc = _doc_with_version(
            admin_user, folder, "preview_err.pdf", b"%PDF-1.4", "application/pdf", "application/pdf"
        )
        real_open = FieldFile.open

        def _open(self, mode="rb"):
            if "preview_err" in (getattr(self, "name", "") or ""):
                raise OSError("e")
            return real_open(self, mode)

        monkeypatch.setattr(FieldFile, "open", _open)
        r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 404

    def test_preview_text_read_error_empty(self, admin_client, admin_user, folder, monkeypatch):
        doc = _doc_with_version(
            admin_user, folder, "preview_err_read.txt", b"x", "text/plain", "text/plain"
        )
        real_read = FieldFile.read

        def _read(self, *a, **k):
            if "preview_err_read" in (getattr(self, "name", "") or ""):
                raise RuntimeError("e")
            return real_read(self, *a, **k)

        monkeypatch.setattr(FieldFile, "read", _read)
        r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200
        assert r.json().get("content") == ""

    def test_preview_office_converted(self, admin_client, admin_user, folder, tmp_path):
        from unittest.mock import patch

        pdf = tmp_path / "out.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        doc = _doc_with_version(
            admin_user,
            folder,
            "w.docx",
            b"PK\x03\x04",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        with patch("apps.documents.viewer.convert_office_to_pdf", return_value=str(pdf)):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200
        assert r["X-Viewer-Type"] == "office"

    def test_preview_office_conversion_fails_503(self, admin_client, admin_user, folder):
        from unittest.mock import patch

        doc = _doc_with_version(
            admin_user,
            folder,
            "w.docx",
            b"PK\x03\x04",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        with patch("apps.documents.viewer.convert_office_to_pdf", side_effect=Exception("lo missing")):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 503

    def test_preview_image_bmp_converts(self, admin_client, admin_user, folder, tmp_path):
        from unittest.mock import patch

        out = tmp_path / "x.png"
        out.write_bytes(b"\x89PNG\r\n\x1a\n")
        doc = _doc_with_version(admin_user, folder, "x.bmp", b"BMP", "image/bmp", "image/bmp")
        with patch("apps.documents.viewer.convert_image_to_web", return_value=(str(out), "image/png")):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200
        assert r["X-Viewer-Type"] == "image"

    def test_preview_video_converts_mp4(self, admin_client, admin_user, folder, tmp_path):
        from unittest.mock import patch

        mp4 = tmp_path / "x.mp4"
        mp4.write_bytes(b"\x00\x00\x00\x18ftypmp42")
        doc = _doc_with_version(admin_user, folder, "x.mov", b"moov", "video/quicktime", "video/quicktime")
        with patch("apps.documents.viewer.convert_video_to_mp4", return_value=str(mp4)):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200
        assert r["X-Viewer-Type"] == "video"

    def test_preview_image_convert_fails_500(self, admin_client, admin_user, folder):
        from unittest.mock import patch

        doc = _doc_with_version(admin_user, folder, "bad.bmp", b"BMP", "image/bmp", "image/bmp")
        with patch("apps.documents.viewer.convert_image_to_web", side_effect=Exception("conv")):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 500

    def test_preview_video_convert_fails_500(self, admin_client, admin_user, folder):
        from unittest.mock import patch

        doc = _doc_with_version(admin_user, folder, "bad.mov", b"m", "video/quicktime", "video/quicktime")
        with patch("apps.documents.viewer.convert_video_to_mp4", side_effect=Exception("ff")):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 500

    def test_preview_audio_inline(self, admin_client, admin_user, folder):
        doc = _doc_with_version(
            admin_user,
            folder,
            "a.mp3",
            b"\xff\xfb",
            "audio/mpeg",
            "audio/mpeg",
        )
        r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200
        assert r["X-Viewer-Type"] == "audio"
