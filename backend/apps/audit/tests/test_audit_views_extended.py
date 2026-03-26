"""Test estesi audit API (FASE 33B)."""
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import AuditLog
from apps.documents.models import Document, DocumentVersion, Folder

User = get_user_model()


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(email="aud-ad@test.com", password="Test123!", role="ADMIN")
    c = APIClient()
    c.force_authenticate(user=u)
    return c, u


@pytest.fixture
def operator_client(db):
    u = User.objects.create_user(email="aud-op@test.com", password="Test123!", role="OPERATOR")
    c = APIClient()
    c.force_authenticate(user=u)
    return c, u


@pytest.mark.django_db
class TestAuditListFilters:
    def test_filter_by_action_and_user(self, admin_client):
        client, admin = admin_client
        other = User.objects.create_user(email="aud-other@test.com", password="x", role="OPERATOR")
        AuditLog.objects.create(user=admin, action="LOGIN", detail={})
        AuditLog.objects.create(user=other, action="LOGOUT", detail={})
        r = client.get("/api/audit/", {"action": "LOGIN"})
        assert r.status_code == 200
        for row in r.json().get("results", []):
            assert row["action"] == "LOGIN"
        r2 = client.get("/api/audit/", {"user_id": str(other.id)})
        assert r2.status_code == 200
        assert all(x["user_id"] == str(other.id) for x in r2.json()["results"])

    def test_filter_by_date(self, admin_client):
        client, admin = admin_client
        AuditLog.objects.create(user=admin, action="LOGIN", detail={})
        today = timezone.now().date().isoformat()
        r = client.get("/api/audit/", {"date_from": today, "date_to": today})
        assert r.status_code == 200
        assert r.json()["count"] >= 1

    def test_pagination_page_size(self, admin_client):
        client, admin = admin_client
        for i in range(3):
            AuditLog.objects.create(user=admin, action="LOGIN", detail={"i": i})
        r = client.get("/api/audit/", {"page": 1, "page_size": 2})
        assert r.status_code == 200
        assert len(r.json()["results"]) <= 2


@pytest.mark.django_db
class TestAuditExportPermissions:
    def test_export_excel_forbidden_for_operator(self, operator_client):
        client, _ = operator_client
        r = client.get("/api/audit/export_excel/")
        assert r.status_code == 403

    def test_export_pdf_forbidden_for_operator(self, operator_client):
        client, _ = operator_client
        r = client.get("/api/audit/export_pdf/")
        assert r.status_code == 403

    def test_export_excel_admin_ok(self, admin_client):
        client, admin = admin_client
        AuditLog.objects.create(user=admin, action="LOGIN", detail={})
        r = client.get("/api/audit/export_excel/")
        assert r.status_code == 200
        assert "spreadsheet" in r["Content-Type"]

    def test_export_pdf_admin_ok(self, admin_client):
        client, admin = admin_client
        AuditLog.objects.create(user=admin, action="LOGIN", detail={})
        r = client.get("/api/audit/export_pdf/")
        assert r.status_code == 200


@pytest.mark.django_db
class TestDocumentActivity:
    def test_document_not_found(self, admin_client):
        client, _ = admin_client
        r = client.get(f"/api/audit/document/{uuid.uuid4()}/")
        assert r.status_code == 404

    def test_activity_for_document(self, admin_client):
        client, admin = admin_client
        folder = Folder.objects.create(name="AF", created_by=admin)
        doc = Document.objects.create(title="D", folder=folder, created_by=admin, owner=admin)
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            created_by=admin,
            is_current=True,
        )
        AuditLog.objects.create(
            user=admin,
            action="DOCUMENT_CREATED",
            detail={"document_id": str(doc.id)},
        )
        r = client.get(f"/api/audit/document/{doc.id}/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1
