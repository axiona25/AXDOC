# FASE 34B — Copertura righe residue signatures/views.py (≥95%)
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
from apps.signatures.views import ConservationRequestViewSet

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="SigR OU", code="SRU", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="sigrem-adm@test.com",
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
        email="sigrem-sg@test.com",
        password="Sign123!",
        role="OPERATOR",
        first_name="S",
        last_name="G",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.fixture
def other_user(db, tenant, ou):
    u = User.objects.create_user(
        email="sigrem-ot@test.com",
        password="Op123456!",
        role="OPERATOR",
        first_name="O",
        last_name="T",
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
def other_client(other_user):
    c = APIClient()
    c.force_authenticate(user=other_user)
    return c


@pytest.fixture
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="SigR F", tenant=tenant, created_by=admin_user)


def _protocol(ou, user):
    y = timezone.now().year
    n = ProtocolCounter.get_next_number(ou, y)
    pid = f"{y}/{ou.code}/{n:04d}"
    now = timezone.now()
    return Protocol.objects.create(
        number=n,
        year=y,
        organizational_unit=ou,
        protocol_id=pid,
        direction="in",
        subject="S",
        sender_receiver="SR",
        registered_at=now,
        registered_by=user,
        status="active",
        protocol_number=pid,
        protocol_date=now,
        created_by=user,
    )


@pytest.mark.django_db
class TestSignaturesViewsRemaining:
    # Copre righe: 70
    def test_list_filter_dossier_target_id(self, admin_client, admin_user, ou):
        d = Dossier.objects.create(
            title="D",
            identifier=f"sd-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        SignatureRequest.objects.create(
            target_type="dossier",
            dossier=d,
            requested_by=admin_user,
            signer=admin_user,
            format="cades",
            status="pending_otp",
        )
        r = admin_client.get("/api/signatures/", {"target_type": "dossier", "target_id": str(d.id)})
        assert r.status_code == 200

    # Copre righe: 108, 126, 129
    @patch("apps.signatures.views._notify")
    def test_request_protocol_invalid_format_and_skipped_signers(self, mock_n, admin_client, admin_user, ou, signer_user):
        p = _protocol(ou, admin_user)
        r = admin_client.post(
            "/api/signatures/request_for_protocol/",
            {
                "protocol_id": str(p.id),
                "signature_type": "unknown_format",
                "signers": [{}, {"user_id": str(signer_user.id), "role_required": "invalid_role"}, {"user_id": str(uuid.uuid4())}],
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED

    # Copre righe: 160, 166, 169, 187, 190, 193, 201-204 (sequential senza step)
    @patch("apps.signatures.views._notify")
    def test_request_dossier_skips_and_sequential_empty_steps(self, mock_n, admin_client, admin_user, ou):
        d = Dossier.objects.create(
            title="DS",
            identifier=f"ds-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        r = admin_client.post(
            "/api/signatures/request_for_dossier/",
            {
                "dossier_id": str(d.id),
                "require_sequential": True,
                "signers": [{}, {"user_id": str(uuid.uuid4())}],
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED

    # Copre righe: 216, 218, 220, 224, 226
    def test_sign_step_branches(self, admin_client, signer_client, signer_user, admin_user, ou):
        p = _protocol(ou, admin_user)
        sig_empty = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            format="cades",
            status="pending_otp",
        )
        assert admin_client.post(f"/api/signatures/{sig_empty.id}/sign_step/", {}).status_code == 400
        sig_done = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            format="cades",
            status="completed",
        )
        assert admin_client.post(f"/api/signatures/{sig_done.id}/sign_step/", {}).status_code == 400
        sig_rej = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            format="cades",
            status="rejected",
        )
        assert admin_client.post(f"/api/signatures/{sig_rej.id}/sign_step/", {}).status_code == 400
        sig_wrong = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            format="cades",
            status="pending_otp",
            current_signer_index=0,
        )
        SignatureSequenceStep.objects.create(
            signature_request=sig_wrong,
            order=0,
            signer=signer_user,
            role_required="any",
            status="pending",
        )
        assert admin_client.post(f"/api/signatures/{sig_wrong.id}/sign_step/", {}).status_code == 403
        sig_signed = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            format="cades",
            status="pending_otp",
            current_signer_index=0,
        )
        SignatureSequenceStep.objects.create(
            signature_request=sig_signed,
            order=0,
            signer=signer_user,
            role_required="any",
            status="signed",
        )
        assert signer_client.post(f"/api/signatures/{sig_signed.id}/sign_step/", {}).status_code == 400

    # Copre righe: 247, 251, 253
    def test_reject_step_branches(self, admin_client, signer_client, signer_user, admin_user, ou):
        p = _protocol(ou, admin_user)
        sig_empty = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=signer_user,
            format="cades",
            status="pending_otp",
        )
        assert signer_client.post(f"/api/signatures/{sig_empty.id}/reject_step/", {"reason": "x"}).status_code == 400
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
        assert admin_client.post(f"/api/signatures/{sig.id}/reject_step/", {"reason": "n"}).status_code == 403
        SignatureSequenceStep.objects.filter(signature_request=sig).update(status="signed")
        assert signer_client.post(f"/api/signatures/{sig.id}/reject_step/", {"reason": "n"}).status_code == 400

    # Copre righe: 302 (verify_otp non documento)
    def test_verify_otp_wrong_target_type(self, admin_client, admin_user, ou, signer_user):
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

    # Copre righe: 317, 321, 323, 331-332
    @patch("apps.signatures.views.get_signature_provider")
    def test_resend_otp_branches(self, mock_gp, signer_client, other_client, signer_user, other_user, admin_user, folder):
        mock_gp.return_value.request_signature.return_value = {"otp_expires_at": timezone.now() + timedelta(minutes=5)}
        doc = Document.objects.create(
            title="RO",
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
            requested_by=other_user,
            signer=signer_user,
            format="pades_invisible",
            status="pending_otp",
            max_otp_resends=5,
            otp_resend_count=0,
        )
        assert other_client.post(f"/api/signatures/{sig.id}/resend_otp/", {}).status_code == status.HTTP_403_FORBIDDEN
        sig.status = "completed"
        sig.save(update_fields=["status"])
        assert signer_client.post(f"/api/signatures/{sig.id}/resend_otp/", {}).status_code == status.HTTP_400_BAD_REQUEST
        sig.status = "pending_otp"
        sig.otp_expires_at = timezone.now() - timedelta(hours=1)
        sig.save(update_fields=["status", "otp_expires_at"])
        assert signer_client.post(f"/api/signatures/{sig.id}/resend_otp/", {}).status_code == status.HTTP_400_BAD_REQUEST
        sig.otp_expires_at = timezone.now() + timedelta(hours=1)
        sig.otp_resend_count = 99
        sig.max_otp_resends = 1
        sig.save(update_fields=["otp_expires_at", "otp_resend_count", "max_otp_resends"])
        assert signer_client.post(f"/api/signatures/{sig.id}/resend_otp/", {}).status_code == status.HTTP_400_BAD_REQUEST
        sig.otp_resend_count = 0
        sig.max_otp_resends = 10
        sig.save(update_fields=["otp_resend_count", "max_otp_resends"])
        from django.db.models.fields.files import FieldFile

        real_path = FieldFile.path

        def _path(self):
            if self.name and "f.pdf" in self.name:
                raise ValueError("x")
            return real_path.__get__(self, type(self))

        with patch.object(FieldFile, "path", property(_path)):
            assert signer_client.post(f"/api/signatures/{sig.id}/resend_otp/", {}).status_code == 200

    # Copre righe: 362
    def test_conservation_list_status_filter(self, admin_client, admin_user, folder):
        from apps.signatures.models import ConservationRequest

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
        ConservationRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=admin_user,
            status="sent",
            provider_request_id="x",
            document_type="d",
            document_date=timezone.now().date(),
        )
        r = admin_client.get("/api/conservation/", {"status": "sent"})
        assert r.status_code == 200

    # Copre righe: 370
    def test_conservation_check_status_forbidden_mock_object(self, other_client, admin_user, folder):
        from apps.signatures.models import ConservationRequest

        doc = Document.objects.create(
            title="CF",
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
        cons = ConservationRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=admin_user,
            status="sent",
            provider_request_id="x",
            document_type="d",
            document_date=timezone.now().date(),
        )
        mock_cons = MagicMock()
        mock_cons.requested_by_id = admin_user.id
        with patch.object(ConservationRequestViewSet, "get_object", return_value=mock_cons):
            r = other_client.post(f"/api/conservation/{cons.id}/check_status/")
        assert r.status_code == status.HTTP_403_FORBIDDEN

    # Copre righe: 469, 472
    def test_extract_p7m_no_file_and_bad_ext(self, admin_client):
        assert admin_client.post("/api/extract_p7m/", {}, format="multipart").status_code == status.HTTP_400_BAD_REQUEST
        f = SimpleUploadedFile("x.txt", b"a", content_type="text/plain")
        assert admin_client.post("/api/extract_p7m/", {"file": f}, format="multipart").status_code == status.HTTP_400_BAD_REQUEST
