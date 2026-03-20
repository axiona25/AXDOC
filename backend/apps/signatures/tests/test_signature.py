"""
Test API firma digitale (RF-075..RF-078) con provider mock. OTP: 123456.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.documents.models import Document, DocumentVersion, Folder
from apps.documents.models import DocumentPermission
from apps.signatures.models import SignatureRequest

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def folder(db):
    return Folder.objects.create(name="F")


@pytest.fixture
def user_requestor(db):
    u = User.objects.create_user(email="req@test.com", password="test")
    u.role = "ADMIN"
    u.save()
    return u


@pytest.fixture
def user_signer(db):
    return User.objects.create_user(email="signer@test.com", password="test")


@pytest.fixture
def doc_approved(db, folder, user_requestor):
    doc = Document.objects.create(
        title="Doc da firmare",
        folder=folder,
        created_by=user_requestor,
        status=Document.STATUS_APPROVED,
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        file_name="f.pdf",
        is_current=True,
        created_by=user_requestor,
    )
    DocumentPermission.objects.create(document=doc, user=user_requestor, can_read=True, can_write=True)
    DocumentPermission.objects.create(document=doc, user=user_signer(db), can_read=True)
    return doc


@pytest.fixture
def user_signer_fix(db):
    return User.objects.create_user(email="signer2@test.com", password="test")


@pytest.mark.django_db
class TestRequestSignature:
    def test_request_signature_creates_pending_otp(self, api_client, user_requestor, user_signer_fix, folder):
        doc = Document.objects.create(
            title="D",
            folder=folder,
            created_by=user_requestor,
            status=Document.STATUS_APPROVED,
        )
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=user_requestor,
        )
        DocumentPermission.objects.create(document=doc, user=user_requestor, can_read=True, can_write=True)
        api_client.force_authenticate(user=user_requestor)
        r = api_client.post(
            f"/api/documents/{doc.id}/request_signature/",
            {"signer_id": str(user_signer_fix.id), "format": "pades_invisible", "reason": "Test"},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        data = r.json()
        assert "signature_request_id" in data
        assert "otp_message" in data
        sig = SignatureRequest.objects.get(id=data["signature_request_id"])
        assert sig.status == "pending_otp"
        assert sig.signer_id == user_signer_fix.id

    def test_document_not_approved_returns_400(self, api_client, user_requestor, user_signer_fix, folder):
        doc = Document.objects.create(
            title="D",
            folder=folder,
            created_by=user_requestor,
            status=Document.STATUS_DRAFT,
        )
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=user_requestor,
        )
        DocumentPermission.objects.create(document=doc, user=user_requestor, can_read=True, can_write=True)
        api_client.force_authenticate(user=user_requestor)
        r = api_client.post(
            f"/api/documents/{doc.id}/request_signature/",
            {"signer_id": str(user_signer_fix.id), "format": "cades"},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestVerifyOtp:
    def test_correct_otp_completes_signature(self, api_client, user_requestor, user_signer_fix, folder):
        doc = Document.objects.create(
            title="D",
            folder=folder,
            created_by=user_requestor,
            status=Document.STATUS_APPROVED,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=user_requestor,
        )
        DocumentPermission.objects.create(document=doc, user=user_requestor, can_read=True, can_write=True)
        DocumentPermission.objects.create(document=doc, user=user_signer_fix, can_read=True)
        sig = SignatureRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=user_requestor,
            signer=user_signer_fix,
            format="pades_invisible",
            status="pending_otp",
            provider_request_id="MOCK-123",
            otp_expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        api_client.force_authenticate(user=user_signer_fix)
        r = api_client.post(
            f"/api/signatures/{sig.id}/verify_otp/",
            {"otp_code": "123456"},
            format="json",
        )
        assert r.status_code == 200
        assert r.json().get("success") is True
        sig.refresh_from_db()
        assert sig.status == "completed"
        assert sig.signed_file

    def test_wrong_otp_increments_attempts(self, api_client, user_signer_fix, user_requestor, folder):
        doc = Document.objects.create(
            title="D",
            folder=folder,
            created_by=user_requestor,
            status=Document.STATUS_APPROVED,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=user_requestor,
        )
        sig = SignatureRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=user_requestor,
            signer=user_signer_fix,
            format="pades_invisible",
            status="pending_otp",
            provider_request_id="MOCK-123",
            otp_expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        api_client.force_authenticate(user=user_signer_fix)
        r = api_client.post(
            f"/api/signatures/{sig.id}/verify_otp/",
            {"otp_code": "000000"},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        sig.refresh_from_db()
        assert sig.otp_attempts == 1

    def test_three_wrong_otp_sets_failed(self, api_client, user_signer_fix, user_requestor, folder):
        doc = Document.objects.create(
            title="D",
            folder=folder,
            created_by=user_requestor,
            status=Document.STATUS_APPROVED,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=user_requestor,
        )
        sig = SignatureRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=user_requestor,
            signer=user_signer_fix,
            format="pades_invisible",
            status="pending_otp",
            provider_request_id="MOCK-123",
            otp_expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        api_client.force_authenticate(user=user_signer_fix)
        for _ in range(3):
            api_client.post(
                f"/api/signatures/{sig.id}/verify_otp/",
                {"otp_code": "000000"},
                format="json",
            )
        sig.refresh_from_db()
        assert sig.status == "failed"


@pytest.mark.django_db
class TestDocumentSignaturesList:
    def test_get_document_signatures(self, api_client, user_requestor, user_signer_fix, folder):
        doc = Document.objects.create(
            title="D",
            folder=folder,
            created_by=user_requestor,
            status=Document.STATUS_APPROVED,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=user_requestor,
        )
        DocumentPermission.objects.create(document=doc, user=user_requestor, can_read=True)
        sig = SignatureRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=user_requestor,
            signer=user_signer_fix,
            format="cades",
            status="completed",
        )
        api_client.force_authenticate(user=user_requestor)
        r = api_client.get(f"/api/documents/{doc.id}/signatures/")
        assert r.status_code == 200
        assert len(r.json()) >= 1
        assert r.json()[0]["format"] == "cades"


@pytest.mark.django_db
class TestVerifySignature:
    def test_verify_returns_mock_data(self, api_client, user_requestor, user_signer_fix, folder):
        doc = Document.objects.create(
            title="D",
            folder=folder,
            created_by=user_requestor,
            status=Document.STATUS_APPROVED,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=user_requestor,
        )
        sig = SignatureRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=user_requestor,
            signer=user_signer_fix,
            format="pades_invisible",
            status="completed",
            provider_request_id="MOCK-123",
        )
        from django.core.files.base import ContentFile
        sig.signed_file.save("signed.pdf", ContentFile(b"mock"), save=True)
        api_client.force_authenticate(user=user_requestor)
        r = api_client.get(f"/api/signatures/{sig.id}/verify/")
        assert r.status_code == 200
        data = r.json()
        assert data.get("valid") is True
        assert "signer_name" in data
