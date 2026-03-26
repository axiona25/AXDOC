"""Test unitari SignatureService / ConservationService (FASE 33D)."""
import base64
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.documents.models import Document, DocumentVersion, Folder
from apps.signatures.models import ConservationRequest, SignatureRequest
from apps.signatures.services import ConservationService, SignatureService

User = get_user_model()


@pytest.fixture
def users_and_doc(db):
    folder = Folder.objects.create(name="Svc F")
    req = User.objects.create_user(email="svc-req@test.com", password="x")
    req.role = "ADMIN"
    req.save()
    signer = User.objects.create_user(email="svc-sign@test.com", password="x")
    doc = Document.objects.create(
        title="Svc doc",
        folder=folder,
        created_by=req,
        status=Document.STATUS_APPROVED,
    )
    ver = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        file_name="f.pdf",
        is_current=True,
        created_by=req,
    )
    ver.file.save("f.pdf", SimpleUploadedFile("f.pdf", b"%PDF-1.4", content_type="application/pdf"), save=True)
    doc.current_version = 1
    doc.save(update_fields=["current_version"])
    return req, signer, doc, ver


@pytest.mark.django_db
class TestSignatureService:
    @patch("apps.signatures.services.get_signature_provider")
    def test_request_creates_pending_otp(self, mock_gp, users_and_doc):
        req, signer, doc, ver = users_and_doc
        prov = MagicMock()
        prov.request_signature.return_value = {
            "provider_request_id": "pid-1",
            "message": "OTP sent",
            "otp_expires_at": timezone.now() + timedelta(minutes=5),
        }
        mock_gp.return_value = prov
        sig, msg = SignatureService.request(doc, ver, req, signer, "pades_invisible", reason="R", location="L")
        assert msg
        assert sig.status == "pending_otp"
        assert sig.provider_request_id == "pid-1"

    @patch("apps.signatures.services.get_signature_provider")
    def test_verify_otp_invalid(self, mock_gp, users_and_doc):
        req, signer, doc, ver = users_and_doc
        prov = MagicMock()
        prov.request_signature.return_value = {"provider_request_id": "p2"}
        mock_gp.return_value = prov
        sig, _ = SignatureService.request(doc, ver, req, signer, "pades_invisible")
        prov.confirm_signature.return_value = {"success": False, "error": "bad otp"}
        ok, err = SignatureService.verify_otp(sig, "000000")
        assert ok is False
        assert "OTP" in err or "bad" in err.lower()

    @patch("apps.signatures.services.get_signature_provider")
    def test_verify_otp_expired(self, mock_gp, users_and_doc):
        req, signer, doc, ver = users_and_doc
        prov = MagicMock()
        prov.request_signature.return_value = {"provider_request_id": "p3"}
        mock_gp.return_value = prov
        sig, _ = SignatureService.request(doc, ver, req, signer, "pades_invisible")
        sig.otp_expires_at = timezone.now() - timedelta(minutes=1)
        sig.save(update_fields=["otp_expires_at"])
        ok, err = SignatureService.verify_otp(sig, "123456")
        assert ok is False
        assert "scaduto" in err.lower()
        sig.refresh_from_db()
        assert sig.status == "expired"

    @patch("apps.signatures.services.get_signature_provider")
    def test_verify_wrong_status(self, mock_gp, users_and_doc):
        req, signer, doc, ver = users_and_doc
        prov = MagicMock()
        prov.request_signature.return_value = {"provider_request_id": "p4"}
        mock_gp.return_value = prov
        sig, _ = SignatureService.request(doc, ver, req, signer, "pades_invisible")
        sig.status = "completed"
        sig.save(update_fields=["status"])
        ok, err = SignatureService.verify_otp(sig, "123456")
        assert ok is False
        assert "OTP" in err or "attesa" in err.lower()

    @patch("apps.signatures.services.get_signature_provider")
    def test_verify_otp_valid_completes(self, mock_gp, users_and_doc):
        req, signer, doc, ver = users_and_doc
        prov = MagicMock()
        prov.request_signature.return_value = {"provider_request_id": "p5"}
        raw = b"%PDF signed"
        prov.confirm_signature.return_value = {
            "success": True,
            "signed_file_base64": base64.b64encode(raw).decode("ascii"),
        }
        mock_gp.return_value = prov
        sig, _ = SignatureService.request(doc, ver, req, signer, "pades_invisible")
        ok, msg = SignatureService.verify_otp(sig, "123456")
        assert ok is True
        assert "successo" in msg.lower()
        sig.refresh_from_db()
        assert sig.status == "completed"

    @patch("apps.signatures.services.get_signature_provider")
    def test_verify_otp_corrupt_base64(self, mock_gp, users_and_doc):
        req, signer, doc, ver = users_and_doc
        prov = MagicMock()
        prov.request_signature.return_value = {"provider_request_id": "p6"}
        prov.confirm_signature.return_value = {"success": True, "signed_file_base64": "!!!not-base64!!!"}
        mock_gp.return_value = prov
        sig, _ = SignatureService.request(doc, ver, req, signer, "pades_invisible")
        ok, err = SignatureService.verify_otp(sig, "123456")
        assert ok is False
        assert "valido" in err.lower() or "file" in err.lower()

    def test_get_document_signature_status(self, users_and_doc):
        req, signer, doc, ver = users_and_doc
        SignatureRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=req,
            signer=signer,
            format="pades_invisible",
            status="pending_otp",
            provider_request_id="x",
        )
        rows = SignatureService.get_document_signature_status(doc)
        assert len(rows) >= 1


@pytest.mark.django_db
class TestConservationService:
    @patch("apps.signatures.services.get_conservation_provider")
    def test_submit_and_check_status(self, mock_gcp, users_and_doc):
        req, _signer, doc, ver = users_and_doc
        cprov = MagicMock()
        cprov.submit_for_conservation.return_value = {"provider_request_id": "c1", "provider_package_id": "pkg"}
        cprov.check_conservation_status.return_value = {
            "status": "completed",
            "certificate_url": "https://cert.example/",
        }
        mock_gcp.return_value = cprov
        cons = ConservationService.submit(
            doc,
            ver,
            req,
            {"document_type": "fattura", "document_date": timezone.now().date()},
        )
        assert cons.provider_request_id == "c1"
        ConservationService.check_status(cons)
        cons.refresh_from_db()
        assert cons.status == "completed"
        assert cons.certificate_url

    @patch("apps.signatures.services.get_conservation_provider")
    def test_check_all_pending(self, mock_gcp, users_and_doc):
        req, _signer, doc, ver = users_and_doc
        cprov = MagicMock()
        cprov.submit_for_conservation.return_value = {"provider_request_id": "c2"}
        cprov.check_conservation_status.return_value = {"status": "completed"}
        mock_gcp.return_value = cprov
        ConservationService.submit(
            doc,
            ver,
            req,
            {"document_type": "doc", "document_date": timezone.now().date()},
        )
        stats = ConservationService.check_all_pending()
        assert stats["checked"] >= 1

    def test_get_document_conservation_status(self, users_and_doc):
        req, _signer, doc, ver = users_and_doc
        ConservationRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=req,
            status="sent",
            provider_request_id="z",
            document_type="doc",
            document_date=timezone.now().date(),
        )
        rows = ConservationService.get_document_conservation_status(doc)
        assert len(rows) >= 1
