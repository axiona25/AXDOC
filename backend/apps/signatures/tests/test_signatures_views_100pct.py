# FASE 34 — Copertura mirata signatures/views.py (>=95%)
import io
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentVersion, Folder
from apps.dossiers.models import Dossier
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.protocols.models import Protocol, ProtocolCounter
from apps.signatures.models import SignatureRequest, SignatureSequenceStep

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="Sig OU", code="SOU", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="sig100-adm@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="S",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def signer_user(db, tenant, ou):
    u = User.objects.create_user(
        email="sig100-sign@test.com",
        password="Sign123!",
        role="OPERATOR",
        first_name="S",
        last_name="I",
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
def signer_client(signer_user):
    c = APIClient()
    c.force_authenticate(user=signer_user)
    return c


@pytest.fixture
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="Sig F", tenant=tenant, created_by=admin_user)


def _protocol(ou, user):
    y = timezone.now().year
    n = ProtocolCounter.get_next_number(ou, y)
    pid = f"{y}/{ou.code}/{n:04d}"
    return Protocol.objects.create(
        number=n,
        year=y,
        organizational_unit=ou,
        protocol_id=pid,
        direction="in",
        subject="Subj",
        sender_receiver="SR",
        registered_at=timezone.now(),
        registered_by=user,
        status="active",
        protocol_number=pid,
        protocol_date=timezone.now(),
        created_by=user,
    )


@pytest.mark.django_db
class TestSignatureQuerysetFilters:
    def test_target_type_protocol_and_document(self, admin_client, admin_user, ou, folder):
        doc = Document.objects.create(
            title="SD",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        p = _protocol(ou, admin_user)
        SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            signer=admin_user,
            format="cades",
            status="pending_otp",
        )
        SignatureRequest.objects.create(
            target_type="document",
            document=doc,
            requested_by=admin_user,
            signer=admin_user,
            format="pades_invisible",
            status="pending_otp",
        )
        r = admin_client.get("/api/signatures/", {"target_type": "protocol", "target_id": str(p.id)})
        assert r.status_code == 200
        r2 = admin_client.get("/api/signatures/", {"target_type": "document", "target_id": str(doc.id)})
        assert r2.status_code == 200
        r3 = admin_client.get("/api/signatures/", {"target_type": "dossier"})
        assert r3.status_code == 200


@pytest.mark.django_db
class TestVerifyAndResendOtp:
    @patch("apps.signatures.views.SignatureService.verify_otp", return_value=(True, "ok"))
    def test_verify_otp_document_ok(self, mock_v, signer_client, signer_user, admin_user, folder):
        doc = Document.objects.create(
            title="VOTP",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_APPROVED,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=admin_user,
        )
        sig = SignatureRequest.objects.create(
            target_type="document",
            document=doc,
            document_version=ver,
            requested_by=admin_user,
            signer=signer_user,
            format="pades_invisible",
            status="pending_otp",
        )
        r = signer_client.post(f"/api/signatures/{sig.id}/verify_otp/", {"otp_code": "123456"}, format="json")
        assert r.status_code == 200

    def test_verify_otp_wrong_target(self, admin_client, admin_user, ou, signer_user):
        p = _protocol(ou, admin_user)
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            signer=signer_user,
            format="cades",
            status="pending_otp",
        )
        r = admin_client.post(f"/api/signatures/{sig.id}/verify_otp/", {"otp_code": "123456"}, format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.signatures.views.get_signature_provider")
    def test_resend_otp_branches(self, mock_gp, signer_client, signer_user, admin_user, folder):
        mock_gp.return_value.request_signature.return_value = {
            "otp_expires_at": timezone.now() + timedelta(minutes=5),
            "message": "sent",
        }
        doc = Document.objects.create(
            title="R",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_APPROVED,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=admin_user,
        )
        ver.file.save("f.pdf", SimpleUploadedFile("f.pdf", b"%PDF", content_type="application/pdf"), save=True)
        sig = SignatureRequest.objects.create(
            target_type="document",
            document=doc,
            document_version=ver,
            requested_by=admin_user,
            signer=signer_user,
            format="pades_invisible",
            status="pending_otp",
            max_otp_resends=5,
            otp_resend_count=0,
        )
        r = signer_client.post(f"/api/signatures/{sig.id}/resend_otp/", {}, format="json")
        assert r.status_code == 200
        sig.refresh_from_db()
        sig.status = "completed"
        sig.save(update_fields=["status"])
        r2 = signer_client.post(f"/api/signatures/{sig.id}/resend_otp/", {}, format="json")
        assert r2.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestRequestForProtocolDossier:
    def test_request_for_protocol_validation(self, admin_client):
        r = admin_client.post("/api/signatures/request_for_protocol/", {}, format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_for_protocol_not_found(self, admin_client):
        r = admin_client.post(
            "/api/signatures/request_for_protocol/",
            {"protocol_id": str(uuid.uuid4()), "signers": [{"user_id": str(uuid.uuid4())}]},
            format="json",
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND

    @patch("apps.signatures.views._notify")
    def test_request_for_protocol_happy(self, mock_notify, admin_client, admin_user, ou, signer_user):
        p = _protocol(ou, admin_user)
        r = admin_client.post(
            "/api/signatures/request_for_protocol/",
            {
                "protocol_id": str(p.id),
                "signers": [{"user_id": str(signer_user.id), "role_required": "bogus"}],
                "require_sequential": True,
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        r2 = admin_client.post(
            "/api/signatures/request_for_protocol/",
            {
                "protocol_id": str(p.id),
                "signers": [{"user_id": str(signer_user.id)}],
                "require_sequential": False,
            },
            format="json",
        )
        assert r2.status_code == status.HTTP_201_CREATED

    def test_request_for_dossier(self, admin_client, admin_user, ou, signer_user):
        d = Dossier.objects.create(
            title="DS",
            identifier=f"sig-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            status="open",
        )
        r = admin_client.post(
            "/api/signatures/request_for_dossier/",
            {
                "dossier_id": str(d.id),
                "signers": [{"user_id": str(signer_user.id)}],
                "require_sequential": False,
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestSignRejectStatusDownload:
    @patch("apps.signatures.views._notify")
    def test_sign_step_and_reject(self, mock_notify, signer_client, signer_user, admin_user, ou):
        p = _protocol(ou, admin_user)
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            format="cades",
            status="pending_otp",
            current_signer_index=0,
        )
        SignatureSequenceStep.objects.create(
            signature_request=sig,
            order=0,
            signer=signer_user,
            role_required="any",
            status="pending",
        )
        r = signer_client.post(
            f"/api/signatures/{sig.id}/sign_step/",
            {"certificate_info": {"k": "v"}},
            format="json",
        )
        assert r.status_code == 200

        sig2 = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            format="cades",
            status="pending_otp",
            current_signer_index=0,
        )
        SignatureSequenceStep.objects.create(
            signature_request=sig2,
            order=0,
            signer=signer_user,
            role_required="any",
            status="pending",
        )
        rj = signer_client.post(f"/api/signatures/{sig2.id}/reject_step/", {"reason": "no"}, format="json")
        assert rj.status_code == 200

    def test_status_detail(self, admin_client, admin_user, ou, signer_user):
        p = _protocol(ou, admin_user)
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            signer=signer_user,
            format="cades",
            status="pending_otp",
        )
        SignatureSequenceStep.objects.create(
            signature_request=sig,
            order=0,
            signer=signer_user,
            role_required="any",
            status="pending",
        )
        r = admin_client.get(f"/api/signatures/{sig.id}/status_detail/")
        assert r.status_code == 200
        assert "sequence_steps" in r.json()

    def test_download_signed_zip_and_simple(self, admin_client, admin_user, ou, folder):
        p = _protocol(ou, admin_user)
        doc1 = Document.objects.create(
            title="D1",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        doc2 = Document.objects.create(
            title="D2",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        p.document = doc1
        p.save(update_fields=["document"])
        p.attachments.add(doc2)
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            format="cades",
            status="completed",
            sign_all_documents=True,
        )
        sig.signed_file.save("x.p7m", SimpleUploadedFile("x.p7m", b"BIN", content_type="application/octet-stream"), save=True)
        sig.signed_file_name = "a.p7m"
        sig.save(update_fields=["signed_file_name"])
        r = admin_client.get(f"/api/signatures/{sig.id}/download_signed/")
        assert r.status_code == 200

    def test_download_signed_missing(self, admin_client, admin_user, ou):
        p = _protocol(ou, admin_user)
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            format="cades",
            status="completed",
        )
        r = admin_client.get(f"/api/signatures/{sig.id}/download_signed/")
        assert r.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestVerifySignatureFile:
    @patch("apps.signatures.views.do_verify_signature", return_value={"valid": True})
    def test_verify_signed_file(self, mock_do, admin_client, admin_user, ou, signer_user):
        p = _protocol(ou, admin_user)
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            signer=signer_user,
            format="cades",
            status="completed",
        )
        sig.signed_file.save("s.p7m", SimpleUploadedFile("s.p7m", b"x", content_type="application/octet-stream"), save=True)
        r = admin_client.get(f"/api/signatures/{sig.id}/verify/")
        assert r.status_code == 200

    def test_verify_no_file(self, admin_client, admin_user, ou, signer_user):
        p = _protocol(ou, admin_user)
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            signer=signer_user,
            format="cades",
            status="pending_otp",
        )
        r = admin_client.get(f"/api/signatures/{sig.id}/verify/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestP7MAPIViews:
    @patch("apps.signatures.verification.verify_p7m", return_value={"valid": True, "signers": []})
    def test_verify_p7m_ok(self, mock_v, admin_client):
        f = SimpleUploadedFile("t.p7m", b"abc", content_type="application/octet-stream")
        r = admin_client.post("/api/verify_p7m/", {"file": f}, format="multipart")
        assert r.status_code == 200

    def test_verify_p7m_no_file(self, admin_client):
        r = admin_client.post("/api/verify_p7m/", {}, format="multipart")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_p7m_wrong_ext(self, admin_client):
        f = SimpleUploadedFile("t.txt", b"abc", content_type="text/plain")
        r = admin_client.post("/api/verify_p7m/", {"file": f}, format="multipart")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.signatures.verification.extract_p7m_content")
    def test_extract_p7m_ok(self, mock_ex, admin_client, tmp_path):
        out = tmp_path / "out.bin"
        out.write_bytes(b"data")
        mock_ex.return_value = {
            "success": True,
            "extracted_path": str(out),
            "original_name": "inner.pdf",
            "content_type": "application/pdf",
        }
        f = SimpleUploadedFile("t.p7m", b"abc", content_type="application/octet-stream")
        r = admin_client.post("/api/extract_p7m/", {"file": f}, format="multipart")
        assert r.status_code == 200

    @patch(
        "apps.signatures.verification.extract_p7m_content",
        return_value={"success": False, "error": "fail"},
    )
    def test_extract_p7m_fail(self, mock_ex, admin_client):
        f = SimpleUploadedFile("t.p7m", b"abc", content_type="application/octet-stream")
        r = admin_client.post("/api/extract_p7m/", {"file": f}, format="multipart")
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestConservationViewSet:
    @patch("apps.signatures.views.ConservationService.check_status")
    def test_check_status_ok(self, mock_chk, admin_client, admin_user, folder):
        doc = Document.objects.create(
            title="C",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=admin_user,
        )
        from apps.signatures.models import ConservationRequest

        cons = ConservationRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=admin_user,
            status="sent",
            provider_request_id="x",
            document_type="d",
            document_date=timezone.now().date(),
        )
        r = admin_client.post(f"/api/conservation/{cons.id}/check_status/")
        assert r.status_code == 200
        mock_chk.assert_called_once()

    def test_check_all_pending_admin_only(self, signer_client, admin_client):
        r = signer_client.post("/api/conservation/check_all_pending/")
        assert r.status_code == status.HTTP_403_FORBIDDEN
        r2 = admin_client.post("/api/conservation/check_all_pending/")
        assert r2.status_code == 200

    def test_check_status_forbidden_non_owner(self, signer_client, admin_user, folder):
        doc = Document.objects.create(
            title="C403",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=admin_user,
        )
        from apps.signatures.models import ConservationRequest

        cons = ConservationRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=admin_user,
            status="sent",
            provider_request_id="x",
            document_type="d",
            document_date=timezone.now().date(),
        )
        r = signer_client.post(f"/api/conservation/{cons.id}/check_status/")
        assert r.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestSignaturesEdgeBranches:
    @patch("apps.notifications.services.NotificationService.send", side_effect=RuntimeError("x"))
    def test_notify_swallows_exception(self, mock_send, admin_client, admin_user, ou, signer_user):
        p = _protocol(ou, admin_user)
        r = admin_client.post(
            "/api/signatures/request_for_protocol/",
            {
                "protocol_id": str(p.id),
                "signers": [{"user_id": str(signer_user.id)}],
                "require_sequential": False,
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED

    def test_verify_signed_file_path_error(self, admin_client, admin_user, ou, signer_user, monkeypatch):
        from django.db.models.fields.files import FieldFile

        p = _protocol(ou, admin_user)
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            signer=signer_user,
            format="cades",
            status="completed",
        )
        sig.signed_file.save(
            "verify_path_err.p7m",
            SimpleUploadedFile("verify_path_err.p7m", b"x", content_type="application/octet-stream"),
            save=True,
        )

        def _path(self):
            if self.name and "verify_path_err" in self.name:
                raise ValueError("no path")
            return self.storage.path(self.name)

        monkeypatch.setattr(FieldFile, "path", property(_path))
        r = admin_client.get(f"/api/signatures/{sig.id}/verify/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_download_signed_io_error(self, admin_client, admin_user, ou, folder, monkeypatch):
        from django.db.models.fields.files import FieldFile

        p = _protocol(ou, admin_user)
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            format="cades",
            status="completed",
        )
        fname = f"dlsig_io_fail_{uuid.uuid4().hex[:8]}.p7m"
        sig.signed_file.save(fname, SimpleUploadedFile(fname, b"x", content_type="application/octet-stream"), save=True)
        real_open = FieldFile.open

        def _open(self, mode="rb"):
            if "dlsig_io_fail_" in (getattr(self, "name", "") or ""):
                raise OSError("e")
            return real_open(self, mode)

        monkeypatch.setattr(FieldFile, "open", _open)
        r = admin_client.get(f"/api/signatures/{sig.id}/download_signed/")
        assert r.status_code == status.HTTP_404_NOT_FOUND

    @patch("apps.signatures.verification.extract_p7m_content")
    def test_extract_p7m_rmdir_oserror_swallowed(self, mock_ex, admin_client, tmp_path, monkeypatch):
        out = tmp_path / "out.bin"
        out.write_bytes(b"data")
        mock_ex.return_value = {
            "success": True,
            "extracted_path": str(out),
            "original_name": "inner.pdf",
            "content_type": "application/pdf",
        }

        def boom(*a, **k):
            raise OSError("not empty")

        monkeypatch.setattr("os.rmdir", boom)
        f = SimpleUploadedFile("t.p7m", b"abc", content_type="application/octet-stream")
        r = admin_client.post("/api/extract_p7m/", {"file": f}, format="multipart")
        assert r.status_code == 200
