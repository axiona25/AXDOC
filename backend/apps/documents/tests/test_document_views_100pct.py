# FASE 34 — Copertura mirata documents/views.py (core, escluso preview → vedi test_document_views_100pct_preview.py)
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from apps.documents.models import Document, DocumentTemplate, DocumentVersion, Folder
from apps.documents.views import DocumentViewSet, _documents_export_queryset
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.signatures.models import SignatureRequest

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="D100 OU", code="D1", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="d100-adm@test.com",
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
        email="d100-op@test.com",
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
def approver_user(db, tenant, ou):
    u = User.objects.create_user(
        email="d100-ap@test.com",
        password="Appr123!",
        role="APPROVER",
        first_name="A",
        last_name="P",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="APPROVER")
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
def approver_client(approver_user):
    c = APIClient()
    c.force_authenticate(user=approver_user)
    return c


@pytest.fixture
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="D100 F", tenant=tenant, created_by=admin_user)


@pytest.mark.django_db
class TestDocumentsExportQueryset:
    def test_export_queryset_filters(self, admin_user, folder):
        Document.objects.create(
            title="ExQ",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            metadata_values={"a": 1},
        )
        factory = APIRequestFactory()
        wsgi = factory.get(
            "/api/documents/export_excel/?folder_id=null&status=DRAFT&created_by=&title=ExQ&metadata_structure_id=&date_from=2020-01-01&date_to=2030-01-01"
        )
        force_authenticate(wsgi, user=admin_user)
        request = Request(wsgi)
        view = DocumentViewSet()
        view.request = request
        view.action = "list"
        qs = _documents_export_queryset(view, request)
        assert qs.model is Document

    def test_export_excel_metadata_fallback_str(self, admin_client, admin_user, folder):
        Document.objects.create(
            title="MetaStr",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            metadata_values={"x": 1},
        )
        with patch("apps.documents.views.json.dumps", side_effect=TypeError("not serializable")):
            r = admin_client.get("/api/documents/export_excel/")
        assert r.status_code == 200


@pytest.mark.django_db
class TestDocumentListAndQueryset:
    def test_list_filters_and_non_paginated(self, admin_client, admin_user, folder):
        Document.objects.create(
            title="L1",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            visibility=Document.VISIBILITY_PERSONAL,
        )
        r = admin_client.get(
            "/api/documents/",
            {
                "folder_id": "null",
                "status": "DRAFT",
                "created_by": str(admin_user.id),
                "title": "L1",
                "ordering": "title",
                "date_from": "2020-01-01",
                "date_to": "2030-12-31",
                "visibility": "personal",
            },
        )
        assert r.status_code == 200
        with patch.object(DocumentViewSet, "paginate_queryset", return_value=None):
            r2 = admin_client.get("/api/documents/")
        assert r2.status_code == 200
        assert isinstance(r2.json(), list)

    def test_get_queryset_section_my_files_and_office(self, operator_client, admin_user, operator_user, ou, folder):
        Document.objects.create(
            title="Mine",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=operator_user,
            visibility=Document.VISIBILITY_PERSONAL,
        )
        Document.objects.create(
            title="Off",
            tenant=folder.tenant,
            folder=folder,
            created_by=operator_user,
            owner=operator_user,
            visibility=Document.VISIBILITY_OFFICE,
        )
        r = operator_client.get("/api/documents/", {"section": "my_files"})
        assert r.status_code == 200
        r2 = operator_client.get("/api/documents/", {"section": "office"})
        assert r2.status_code == 200


@pytest.mark.django_db
class TestBulkActions:
    def test_bulk_delete_move_status(self, admin_client, admin_user, folder):
        d1 = Document.objects.create(
            title="B1",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        d2 = Document.objects.create(
            title="B2",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        assert admin_client.post("/api/documents/bulk_delete/", {"document_ids": []}, format="json").status_code == 400
        assert admin_client.post("/api/documents/bulk_move/", {"document_ids": [str(d1.id)]}, format="json").status_code == 400
        assert (
            admin_client.post(
                "/api/documents/bulk_move/",
                {"document_ids": [str(d1.id)], "folder_id": str(uuid.uuid4())},
                format="json",
            ).status_code
            == 404
        )
        r = admin_client.post("/api/documents/bulk_move/", {"document_ids": [str(d1.id)], "folder_id": None}, format="json")
        assert r.status_code == 200
        r2 = admin_client.post(
            "/api/documents/bulk_status/",
            {"document_ids": [str(d1.id), str(d2.id)], "status": Document.STATUS_ARCHIVED},
            format="json",
        )
        assert r2.status_code == 200
        assert admin_client.post("/api/documents/bulk_status/", {"document_ids": [str(d1.id)], "status": "INVALID"}, format="json").status_code == 400


@pytest.mark.django_db
class TestCreateAndP7M:
    @patch("apps.documents.tasks.process_uploaded_file.delay")
    @patch("apps.signatures.verification.verify_p7m", return_value={"valid": True, "signers": [{"n": "1"}]})
    def test_create_p7m_metadata(self, mock_p7m, mock_delay, admin_client, admin_user, folder):
        f = SimpleUploadedFile("x.p7m", b"abc", content_type="application/pkcs7-mime")
        with patch("apps.documents.views.os.path.isfile", return_value=True):
            r = admin_client.post(
                "/api/documents/",
                {"title": "P7", "folder_id": str(folder.id), "file": f},
                format="multipart",
            )
        assert r.status_code == status.HTTP_201_CREATED

    @patch("apps.documents.tasks.process_uploaded_file.delay")
    def test_create_allowed_users_json_string(self, mock_delay, admin_client, admin_user, folder, operator_user):
        f = SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf")
        r = admin_client.post(
            "/api/documents/",
            {
                "file": f,
                "allowed_users": f'["{operator_user.id}"]',
                "allowed_ous": "[]",
            },
            format="multipart",
        )
        assert r.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestClassifyAndOcr:
    def test_classify_text_short(self, admin_client):
        r = admin_client.post("/api/documents/classify_text/", {"text": "short"}, format="json")
        assert r.status_code == 400

    @patch("apps.documents.classification_service.DocumentClassificationService.classify", return_value={"workflow_suggestion": None})
    def test_classify_text_ok(self, mock_c, admin_client):
        r = admin_client.post("/api/documents/classify_text/", {"text": "x" * 20}, format="json")
        assert r.status_code == 200

    @patch("apps.documents.tasks.process_document_text_extraction.delay")
    def test_run_ocr(self, mock_d, admin_client, admin_user, folder):
        doc = Document.objects.create(
            title="OCR",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v.file.save("a.pdf", SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf"), save=True)
        r = admin_client.post(f"/api/documents/{doc.id}/run_ocr/")
        assert r.status_code == 200


@pytest.mark.django_db
class TestDocumentTemplateViewSet:
    def test_template_operator_cannot_mutate(self, operator_client, admin_user):
        tpl = DocumentTemplate.objects.create(name="Tpl X", is_active=True, created_by=admin_user)
        r = operator_client.post("/api/document-templates/", {"name": "Bad", "is_active": True}, format="json")
        assert r.status_code == status.HTTP_403_FORBIDDEN
        r2 = operator_client.patch(f"/api/document-templates/{tpl.id}/", {"name": "Y"}, format="json")
        assert r2.status_code == status.HTTP_403_FORBIDDEN
        r3 = operator_client.delete(f"/api/document-templates/{tpl.id}/")
        assert r3.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestSendConservation:
    @patch("apps.signatures.services.ConservationService.submit")
    def test_send_to_conservation_happy(self, mock_sub, approver_client, approver_user, folder):
        from unittest.mock import MagicMock

        mock_sub.return_value = MagicMock(id=uuid.uuid4(), status="sent")
        doc = Document.objects.create(
            title="Cons",
            tenant=folder.tenant,
            folder=folder,
            created_by=approver_user,
            owner=approver_user,
            status=Document.STATUS_APPROVED,
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=approver_user,
        )
        SignatureRequest.objects.create(
            document=doc,
            document_version=v,
            requested_by=approver_user,
            signer=approver_user,
            format="pades_invisible",
            status="completed",
        )
        r = approver_client.post(
            f"/api/documents/{doc.id}/send_to_conservation/",
            {"document_type": "fattura", "document_date": timezone.now().date().isoformat()},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
