"""
Test API conservazione digitale (RF-079, RF-080) con provider mock.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.documents.models import Document, DocumentVersion, Folder
from apps.documents.models import DocumentPermission
from apps.signatures.models import SignatureRequest, ConservationRequest

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def folder(db):
    return Folder.objects.create(name="F")


@pytest.fixture
def user_admin(db):
    u = User.objects.create_user(email="admin_cons@test.com", password="test")
    u.role = "ADMIN"
    u.save()
    return u


@pytest.fixture
def doc_with_signature(db, folder, user_admin):
    doc = Document.objects.create(
        title="Doc conservazione",
        folder=folder,
        created_by=user_admin,
        status=Document.STATUS_APPROVED,
    )
    ver = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        file_name="f.pdf",
        is_current=True,
        created_by=user_admin,
    )
    DocumentPermission.objects.create(document=doc, user=user_admin, can_read=True, can_write=True)
    sig = SignatureRequest.objects.create(
        document=doc,
        document_version=ver,
        requested_by=user_admin,
        signer=user_admin,
        format="pades_invisible",
        status="completed",
        provider_request_id="MOCK-1",
    )
    return doc


@pytest.mark.django_db
class TestSendToConservation:
    def test_send_to_conservation_creates_request(self, api_client, user_admin, doc_with_signature):
        api_client.force_authenticate(user=user_admin)
        r = api_client.post(
            f"/api/documents/{doc_with_signature.id}/send_to_conservation/",
            {
                "document_type": "Contratto",
                "document_date": "2024-03-10",
                "reference_number": "2024/IT/0001",
                "conservation_class": "1",
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        data = r.json()
        assert data["status"] == "sent"
        assert "conservation_request_id" in data
        cons = ConservationRequest.objects.get(id=data["conservation_request_id"])
        assert cons.document_id == doc_with_signature.id

    def test_without_signature_returns_400(self, api_client, user_admin, folder):
        doc = Document.objects.create(
            title="D",
            folder=folder,
            created_by=user_admin,
            status=Document.STATUS_APPROVED,
        )
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=user_admin,
        )
        DocumentPermission.objects.create(document=doc, user=user_admin, can_read=True)
        api_client.force_authenticate(user=user_admin)
        r = api_client.post(
            f"/api/documents/{doc.id}/send_to_conservation/",
            {"document_type": "Contratto", "document_date": "2024-03-10"},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert "firma" in (r.json().get("detail") or "").lower()

    def test_document_not_approved_returns_400(self, api_client, user_admin, folder):
        doc = Document.objects.create(
            title="D",
            folder=folder,
            created_by=user_admin,
            status=Document.STATUS_DRAFT,
        )
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=user_admin,
        )
        DocumentPermission.objects.create(document=doc, user=user_admin, can_read=True)
        api_client.force_authenticate(user=user_admin)
        r = api_client.post(
            f"/api/documents/{doc.id}/send_to_conservation/",
            {"document_type": "Contratto", "document_date": "2024-03-10"},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCheckConservationStatus:
    def test_check_status_updates_to_completed(self, api_client, user_admin, doc_with_signature):
        ver = doc_with_signature.versions.filter(is_current=True).first()
        cons = ConservationRequest.objects.create(
            document=doc_with_signature,
            document_version=ver,
            requested_by=user_admin,
            status="sent",
            provider_request_id="CONS-MOCK-123",
            document_type="Contratto",
            document_date=doc_with_signature.created_at.date(),
        )
        api_client.force_authenticate(user=user_admin)
        r = api_client.post(f"/api/conservation/{cons.id}/check_status/")
        assert r.status_code == 200
        cons.refresh_from_db()
        assert cons.status == "completed"
        assert cons.certificate_url
