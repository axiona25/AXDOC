"""Test estesi DocumentViewSet — action con bassa copertura (FASE 33C)."""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentVersion, Folder
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership
from apps.organizations.models import Tenant
from apps.workflows.models import WorkflowStep, WorkflowTemplate

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Organizzazione Default", "plan": "enterprise"},
    )
    return t


@pytest.fixture
def ou(db, tenant):
    o = OrganizationalUnit.objects.create(name="DV OU", code="DVU", tenant=tenant)
    return o


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="adm-dv@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="D",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def operator_user(db, tenant, ou):
    u = User.objects.create_user(
        email="op-dv@test.com",
        password="Op123456!",
        role="OPERATOR",
        first_name="O",
        last_name="P",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def operator_client(operator_user):
    c = APIClient()
    c.force_authenticate(user=operator_user)
    return c


@pytest.fixture
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="DV Folder", tenant=tenant, created_by=admin_user)


@pytest.fixture
def document(db, tenant, admin_user, folder):
    d = Document.objects.create(
        title="Test Doc Views Ext",
        tenant=tenant,
        folder=folder,
        created_by=admin_user,
        owner=admin_user,
        status=Document.STATUS_DRAFT,
    )
    return d


@pytest.fixture
def document_with_file(db, document, admin_user):
    v = DocumentVersion.objects.create(
        document=document,
        version_number=1,
        file_name="x.txt",
        file_type="text/plain",
        file_size=4,
        checksum="a" * 64,
        created_by=admin_user,
        is_current=True,
    )
    v.file.save("x.txt", SimpleUploadedFile("x.txt", b"text", content_type="text/plain"), save=True)
    document.current_version = 1
    document.save(update_fields=["current_version"])
    return document


@pytest.mark.django_db
class TestDocumentListFilters:
    def test_list_status_and_title_filters(self, admin_client, document):
        r = admin_client.get("/api/documents/", {"status": "DRAFT", "title": "Views Ext"})
        assert r.status_code == 200
        data = r.json()
        rows = data.get("results", data)
        assert len(rows) >= 1

    def test_list_ordering(self, admin_client, document):
        r = admin_client.get("/api/documents/", {"ordering": "title"})
        assert r.status_code == 200

    def test_my_files_tree(self, admin_client, document):
        r = admin_client.get("/api/documents/my_files_tree/")
        assert r.status_code == 200
        body = r.json()
        assert "personal" in body and "office" in body


@pytest.mark.django_db
class TestDocumentSideActions:
    def test_workflow_history_empty(self, admin_client, document):
        r = admin_client.get(f"/api/documents/{document.id}/workflow_history/")
        assert r.status_code == 200
        assert r.json() == []

    def test_signatures_list_empty(self, admin_client, document):
        r = admin_client.get(f"/api/documents/{document.id}/signatures/")
        assert r.status_code == 200
        assert r.json() == []

    def test_conservation_list_empty(self, admin_client, document):
        r = admin_client.get(f"/api/documents/{document.id}/conservation/")
        assert r.status_code == 200
        assert r.json() == []

    def test_visibility_patch(self, admin_client, document):
        r = admin_client.patch(
            f"/api/documents/{document.id}/visibility/",
            {"visibility": "office"},
            format="json",
        )
        assert r.status_code == 200
        document.refresh_from_db()
        assert document.visibility == "office"

    def test_share_external_and_shares_list(self, admin_client, document):
        r = admin_client.post(
            f"/api/documents/{document.id}/share/",
            {
                "recipient_type": "external",
                "recipient_email": "ext@example.com",
                "recipient_name": "Ext",
            },
            format="json",
        )
        assert r.status_code == 201
        r2 = admin_client.get(f"/api/documents/{document.id}/shares/")
        assert r2.status_code == 200
        assert len(r2.json()) >= 1

    def test_chat_room_for_document(self, admin_client, document):
        r = admin_client.post(f"/api/documents/{document.id}/chat/", {}, format="json")
        assert r.status_code == 200
        assert "id" in r.json()

    def test_protocollo_shortcut(self, admin_client, document_with_file, ou):
        d = document_with_file
        r = admin_client.post(
            f"/api/documents/{d.id}/protocollo/",
            {
                "organizational_unit_id": str(ou.id),
                "subject": "Oggetto protocollazione test",
                "sender_receiver": "Mario",
            },
            format="json",
        )
        assert r.status_code == 201
        d.refresh_from_db()
        assert d.is_protocolled is True

    def test_start_workflow_on_document(self, admin_client, document, admin_user):
        tpl = WorkflowTemplate.objects.create(name="Tpl DV Ext", created_by=admin_user, is_published=True)
        WorkflowStep.objects.create(
            template=tpl,
            name="Step1",
            order=1,
            action="review",
            assignee_type="role",
            assignee_role="ADMIN",
        )
        r = admin_client.post(
            f"/api/documents/{document.id}/start_workflow/",
            {"template_id": str(tpl.id)},
            format="json",
        )
        assert r.status_code == 201
        document.refresh_from_db()
        assert document.status == Document.STATUS_IN_REVIEW

    def test_workflow_action_no_active(self, admin_client, document):
        r = admin_client.post(
            f"/api/documents/{document.id}/workflow_action/",
            {"action": "approve"},
            format="json",
        )
        assert r.status_code == 400

    def test_bulk_move_to_root(self, admin_client, document, folder):
        document.folder = folder
        document.save(update_fields=["folder"])
        r = admin_client.post(
            "/api/documents/bulk_move/",
            {"document_ids": [str(document.id)], "folder_id": None},
            format="json",
        )
        assert r.status_code == 200
        document.refresh_from_db()
        assert document.folder_id is None


@pytest.mark.django_db
class TestRunOcrExtended:
    @patch("apps.documents.tasks.process_document_text_extraction.delay")
    def test_run_ocr_triggers_task(self, mock_delay, admin_client, document_with_file):
        r = admin_client.post(f"/api/documents/{document_with_file.id}/run_ocr/", {}, format="json")
        assert r.status_code == 200
        mock_delay.assert_called_once()
