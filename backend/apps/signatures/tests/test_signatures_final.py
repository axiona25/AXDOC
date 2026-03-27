# Copertura: signatures/* righe residue FASE 35D.2
import base64
import uuid
from datetime import timedelta
from unittest.mock import PropertyMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentVersion, Folder
from apps.dossiers.models import Dossier, DossierDocument
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.protocols.models import Protocol, ProtocolAttachment, ProtocolCounter
from apps.signatures.models import ConservationRequest, SignatureRequest, SignatureSequenceStep
from apps.signatures.providers.aruba_provider import ArubaConservationProvider, ArubaSignatureProvider
from apps.signatures.providers.factory import get_conservation_provider, get_signature_provider
from apps.signatures.providers.mock_provider import MockSignatureProvider
from apps.signatures.serializers import OTPVerifySerializer
from apps.signatures.services import ConservationService, SignatureService

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="SigFin OU", code="SFO", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="sigfin-adm@test.com",
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
def signer_user(db, tenant, ou):
    u = User.objects.create_user(
        email="sigfin-sign@test.com",
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
    return Folder.objects.create(name="SigFin F", tenant=tenant, created_by=admin_user)


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
class TestSignatureModelsFinal:
    def test_str_and_target_display(self, admin_user, folder, ou):
        doc = Document.objects.create(
            title="T1", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        p = _protocol(ou, admin_user)
        d = Dossier.objects.create(title="D", identifier="DSF-1", created_by=admin_user, responsible=admin_user)
        sr1 = SignatureRequest.objects.create(
            target_type="document",
            document=doc,
            requested_by=admin_user,
            signer=admin_user,
            format="cades",
            status="pending_otp",
        )
        assert "Firma" in str(sr1) and "T1" in str(sr1)
        assert doc.title in sr1.get_target_display()
        sr2 = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            signer=admin_user,
            format="cades",
            status="pending_otp",
        )
        assert p.protocol_id in sr2.get_target_display()
        sr3 = SignatureRequest.objects.create(
            target_type="dossier",
            dossier=d,
            requested_by=admin_user,
            signer=admin_user,
            format="cades",
            status="pending_otp",
        )
        assert d.identifier in sr3.get_target_display()
        sr4 = SignatureRequest.objects.create(
            target_type="document",
            requested_by=admin_user,
            signer=admin_user,
            format="cades",
            status="pending_otp",
        )
        assert str(sr4.id) in sr4.get_target_display()
        step = SignatureSequenceStep.objects.create(
            signature_request=sr1, order=0, signer=admin_user, status="pending"
        )
        assert admin_user.email in str(step)
        cons = ConservationRequest.objects.create(
            document=doc,
            document_version=DocumentVersion.objects.create(
                document=doc,
                version_number=1,
                file_name="a.pdf",
                file_size=1,
                file_type="application/pdf",
                is_current=True,
                created_by=admin_user,
            ),
            requested_by=admin_user,
            document_type="dt",
            document_date=timezone.now().date(),
        )
        assert doc.title in str(cons)

    def test_advance_sequence_skips_non_pending_steps(self, admin_user, signer_user, folder, ou):
        p = _protocol(ou, admin_user)
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            signer=signer_user,
            format="cades",
            status="pending_otp",
            current_signer_index=0,
        )
        SignatureSequenceStep.objects.create(
            signature_request=sig, order=0, signer=admin_user, status="signed"
        )
        SignatureSequenceStep.objects.create(
            signature_request=sig, order=1, signer=signer_user, status="signed"
        )
        SignatureSequenceStep.objects.create(
            signature_request=sig, order=2, signer=admin_user, status="pending"
        )
        sig.advance_sequence()
        sig.refresh_from_db()
        assert sig.current_signer_index == 2

    def test_advance_sequence_no_steps(self, admin_user, folder):
        doc = Document.objects.create(
            title="T2", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        sr = SignatureRequest.objects.create(
            target_type="document",
            document=doc,
            requested_by=admin_user,
            signer=admin_user,
            format="cades",
            status="pending_otp",
        )
        sr.advance_sequence()
        sr.refresh_from_db()
        assert sr.status == "completed"

    def test_get_all_target_documents_branches(self, admin_user, signer_user, folder, ou):
        doc = Document.objects.create(
            title="TD", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            file_size=1,
            file_type="application/pdf",
            is_current=True,
            created_by=admin_user,
        )
        sr_doc = SignatureRequest.objects.create(
            target_type="document",
            document=doc,
            document_version=v,
            requested_by=admin_user,
            signer=signer_user,
            format="cades",
            status="pending_otp",
        )
        pairs = sr_doc.get_all_target_documents()
        assert len(pairs) == 1 and pairs[0][0] == doc
        sr_doc.document = None
        assert sr_doc.get_all_target_documents() == []
        p = _protocol(ou, admin_user)
        doc2 = Document.objects.create(
            title="Att", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        DocumentVersion.objects.create(
            document=doc2,
            version_number=1,
            file_name="b.pdf",
            file_size=1,
            file_type="application/pdf",
            is_current=True,
            created_by=admin_user,
        )
        p.document = doc2
        p.save(update_fields=["document"])
        sr_p = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            signer=admin_user,
            format="cades",
            status="pending_otp",
            sign_all_documents=True,
        )
        ProtocolAttachment.objects.create(protocol=p, document=doc2)
        out = sr_p.get_all_target_documents()
        assert len(out) >= 1
        dos = Dossier.objects.create(title="Dx", identifier="DX-99", created_by=admin_user, responsible=admin_user)
        DossierDocument.objects.create(dossier=dos, document=doc, added_by=admin_user)
        sr_d = SignatureRequest.objects.create(
            target_type="dossier",
            dossier=dos,
            requested_by=admin_user,
            signer=admin_user,
            format="cades",
            status="pending_otp",
        )
        assert len(sr_d.get_all_target_documents()) >= 1
        doc_nv = Document.objects.create(
            title="NoVer", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        sr_nv = SignatureRequest.objects.create(
            target_type="document",
            document=doc_nv,
            requested_by=admin_user,
            signer=admin_user,
            format="cades",
            status="pending_otp",
        )
        pairs = sr_nv.get_all_target_documents()
        assert pairs == [(doc_nv, None)]
        dos_empty = Dossier.objects.create(title="De", identifier="DX-E", created_by=admin_user, responsible=admin_user)
        sr_empty = SignatureRequest.objects.create(
            target_type="dossier",
            dossier=dos_empty,
            requested_by=admin_user,
            signer=admin_user,
            format="cades",
            status="pending_otp",
        )
        assert sr_empty.get_all_target_documents() == []


@pytest.mark.django_db
class TestSignatureServicesFinal:
    def test_request_doc_path_oserror(self, admin_user, signer_user, folder, tmp_path):
        doc = Document.objects.create(
            title="P1", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        p = tmp_path / "x.pdf"
        p.write_bytes(b"%PDF-1.4")
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            file_size=p.stat().st_size,
            file_type="application/pdf",
            is_current=True,
            created_by=admin_user,
        )
        ver.file.save("x.pdf", ContentFile(p.read_bytes()), save=True)
        with patch("apps.signatures.services.os.path.isfile", side_effect=OSError("x")):
            sig, _ = SignatureService.request(doc, ver, admin_user, signer_user, "cades")
        assert sig.status == "pending_otp"

    def test_verify_otp_branches(self, admin_user, signer_user, folder, tmp_path):
        def _mk_sig():
            doc = Document.objects.create(
                title=f"P2-{uuid.uuid4().hex[:8]}",
                tenant=folder.tenant,
                folder=folder,
                created_by=admin_user,
                owner=admin_user,
            )
            p = tmp_path / f"y-{uuid.uuid4().hex[:8]}.pdf"
            p.write_bytes(b"%PDF-1.4")
            ver = DocumentVersion.objects.create(
                document=doc,
                version_number=1,
                file_name="y.pdf",
                file_size=p.stat().st_size,
                file_type="application/pdf",
                is_current=True,
                created_by=admin_user,
            )
            ver.file.save("y.pdf", ContentFile(p.read_bytes()), save=True)
            return SignatureService.request(doc, ver, admin_user, signer_user, "cades")[0]

        sig = _mk_sig()
        sig.status = "completed"
        sig.save(update_fields=["status"])
        ok, msg = SignatureService.verify_otp(sig, "123456")
        assert ok is False and "non in attesa" in msg

        sig = _mk_sig()
        sig.otp_expires_at = timezone.now() - timedelta(minutes=1)
        sig.save(update_fields=["otp_expires_at"])
        ok, msg = SignatureService.verify_otp(sig, "123456")
        assert ok is False and "scaduto" in msg

        sig = _mk_sig()
        sig.otp_attempts = 3
        sig.save(update_fields=["otp_attempts"])
        ok, msg = SignatureService.verify_otp(sig, "123456")
        assert ok is False and "Troppi" in msg

        sig = _mk_sig()
        with patch("apps.signatures.services.get_signature_provider") as gp:
            gp.return_value.confirm_signature.return_value = {"success": False, "error": "bad"}
            ok, msg = SignatureService.verify_otp(sig, "123456")
            assert ok is False

        sig = _mk_sig()
        sig.otp_attempts = 2
        sig.save(update_fields=["otp_attempts"])
        with patch("apps.signatures.services.get_signature_provider") as gp:
            gp.return_value.confirm_signature.return_value = {"success": False, "error": "bad"}
            SignatureService.verify_otp(sig, "999999")
            sig.refresh_from_db()
            assert sig.status == "failed"

        sig = _mk_sig()
        with patch("apps.signatures.services.get_signature_provider") as gp:
            gp.return_value.confirm_signature.return_value = {"success": True, "signed_file_base64": None}
            ok, msg = SignatureService.verify_otp(sig, "123456")
            assert ok is False and "non ricevuto" in msg

        sig = _mk_sig()
        with patch("apps.signatures.services.get_signature_provider") as gp:
            gp.return_value.confirm_signature.return_value = {"success": True, "signed_file_base64": "!!!"}
            with patch("apps.signatures.services.base64.b64decode", side_effect=ValueError("bad b64")):
                ok, msg = SignatureService.verify_otp(sig, "123456")
                assert ok is False

    def test_conservation_submit_path_except(self, admin_user, folder, tmp_path):
        doc = Document.objects.create(
            title="C1", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        p = tmp_path / "c.pdf"
        p.write_bytes(b"%PDF-1.4")
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="c.pdf",
            file_size=p.stat().st_size,
            file_type="application/pdf",
            is_current=True,
            created_by=admin_user,
        )
        ver.file.save("c.pdf", ContentFile(p.read_bytes()), save=True)
        with patch("apps.signatures.services.os.path.isfile", side_effect=OSError("e")):
            cr = ConservationService.submit(
                doc,
                ver,
                admin_user,
                {
                    "document_type": "t",
                    "document_date": timezone.now().date(),
                    "reference_number": "",
                    "conservation_class": "1",
                },
            )
        assert cr.status == "sent"

    def test_conservation_check_status_failed_message(self, admin_user, folder):
        doc = Document.objects.create(
            title="C2", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="c.pdf",
            file_size=1,
            file_type="application/pdf",
            is_current=True,
            created_by=admin_user,
        )
        cr = ConservationRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=admin_user,
            status="sent",
            document_type="t",
            document_date=timezone.now().date(),
            provider_request_id="x",
        )
        with patch("apps.signatures.services.get_conservation_provider") as gp:
            gp.return_value.check_conservation_status.return_value = {
                "status": "failed",
                "message": "err",
            }
            ConservationService.check_status(cr)
        cr.refresh_from_db()
        assert cr.error_message == "err"

    def test_check_all_pending_counts(self, admin_user, folder):
        doc = Document.objects.create(
            title="C3", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="c.pdf",
            file_size=1,
            file_type="application/pdf",
            is_current=True,
            created_by=admin_user,
        )
        ConservationRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=admin_user,
            status="sent",
            document_type="t",
            document_date=timezone.now().date(),
            provider_request_id="a",
        )
        with patch.object(ConservationService, "check_status", side_effect=lambda r: r):
            out = ConservationService.check_all_pending()
        assert out["checked"] >= 1
        doc_f = Document.objects.create(
            title="CF", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        ver_f = DocumentVersion.objects.create(
            document=doc_f,
            version_number=1,
            file_name="c.pdf",
            file_size=1,
            file_type="application/pdf",
            is_current=True,
            created_by=admin_user,
        )
        cr_f = ConservationRequest.objects.create(
            document=doc_f,
            document_version=ver_f,
            requested_by=admin_user,
            status="in_progress",
            document_type="t",
            document_date=timezone.now().date(),
            provider_request_id="fail-me",
        )
        with patch("apps.signatures.services.get_conservation_provider") as gp:
            gp.return_value.check_conservation_status.return_value = {"status": "failed", "message": "x"}
            out2 = ConservationService.check_all_pending()
        assert out2["failed"] >= 1


@pytest.mark.django_db
class TestSignatureProvidersFinal:
    def test_factory_aruba(self):
        with override_settings(SIGNATURE_PROVIDER="aruba", CONSERVATION_PROVIDER="aruba"):
            assert isinstance(get_signature_provider(), ArubaSignatureProvider)
            assert isinstance(get_conservation_provider(), ArubaConservationProvider)

    def test_aruba_raises(self):
        a = ArubaSignatureProvider()
        with pytest.raises(NotImplementedError):
            a.request_signature("", "+39", "cades")
        with pytest.raises(NotImplementedError):
            a.confirm_signature("id", "123456")
        with pytest.raises(NotImplementedError):
            a.verify_signature("/x.p7m")
        c = ArubaConservationProvider()
        with pytest.raises(NotImplementedError):
            c.submit_for_conservation("", {})
        with pytest.raises(NotImplementedError):
            c.check_conservation_status("id")

    def test_mock_verify_signature_called(self):
        m = MockSignatureProvider()
        r = m.verify_signature("/tmp/x.p7m")
        assert r["valid"] is True


@pytest.mark.django_db
class TestSignatureSerializersFinal:
    def test_otp_invalid_format(self):
        s = OTPVerifySerializer(data={"otp_code": "abc12"})
        assert s.is_valid() is False


@pytest.mark.django_db
class TestSignatureViewsFinal:
    def test_list_and_retrieve_serializer_routing(self, admin_client, admin_user, folder):
        doc = Document.objects.create(
            title="SR", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        sig = SignatureRequest.objects.create(
            target_type="document",
            document=doc,
            requested_by=admin_user,
            signer=admin_user,
            format="cades",
            status="pending_otp",
        )
        r_list = admin_client.get("/api/signatures/")
        assert r_list.status_code == status.HTTP_200_OK
        r_det = admin_client.get(f"/api/signatures/{sig.id}/")
        assert r_det.status_code == status.HTTP_200_OK
        assert "otp_attempts" in (r_det.json() or {})

    def test_sign_step_completed_or_rejected(self, admin_client, signer_client, admin_user, signer_user, ou, folder):
        p = _protocol(ou, admin_user)
        sig_done = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            signer=signer_user,
            format="cades",
            status="completed",
        )
        SignatureSequenceStep.objects.create(
            signature_request=sig_done, order=0, signer=signer_user, status="pending"
        )
        assert admin_client.post(f"/api/signatures/{sig_done.id}/sign_step/", {}, format="json").status_code == 400
        sig_rej = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=p,
            requested_by=admin_user,
            signer=signer_user,
            format="cades",
            status="rejected",
        )
        SignatureSequenceStep.objects.create(
            signature_request=sig_rej, order=0, signer=signer_user, status="pending"
        )
        assert admin_client.post(f"/api/signatures/{sig_rej.id}/sign_step/", {}, format="json").status_code == 400

    def test_request_for_dossier_errors_and_role(self, admin_client, admin_user, signer_user, ou):
        d = Dossier.objects.create(title="DF", identifier="DF-1", created_by=admin_user, responsible=admin_user)
        r = admin_client.post("/api/signatures/request_for_dossier/", {}, format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        r = admin_client.post("/api/signatures/request_for_dossier/", {"dossier_id": str(d.id)}, format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        r = admin_client.post(
            "/api/signatures/request_for_dossier/",
            {
                "dossier_id": str(d.id),
                "signers": [{"user_id": str(signer_user.id), "role_required": "invalid"}],
                "format": "not_a_real_format",
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED

    def test_verify_otp_forbidden_wrong_signer(self, admin_client, signer_client, admin_user, signer_user, folder):
        doc = Document.objects.create(
            title="VO", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="v.pdf",
            file_size=1,
            file_type="application/pdf",
            is_current=True,
            created_by=admin_user,
        )
        sig = SignatureRequest.objects.create(
            target_type="document",
            document=doc,
            document_version=ver,
            requested_by=admin_user,
            signer=signer_user,
            format="cades",
            status="pending_otp",
        )
        r = admin_client.post(f"/api/signatures/{sig.id}/verify_otp/", {"otp_code": "123456"}, format="json")
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_resend_otp_path_except_and_no_signer(self, signer_client, admin_user, signer_user, folder, tmp_path):
        doc = Document.objects.create(
            title="RO", tenant=folder.tenant, folder=folder, created_by=admin_user, owner=admin_user
        )
        p = tmp_path / "r.pdf"
        p.write_bytes(b"%PDF-1.4")
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="r.pdf",
            file_size=p.stat().st_size,
            file_type="application/pdf",
            is_current=True,
            created_by=admin_user,
        )
        ver.file.save("r.pdf", ContentFile(p.read_bytes()), save=True)
        sig = SignatureRequest.objects.create(
            target_type="document",
            document=doc,
            document_version=ver,
            requested_by=admin_user,
            signer=signer_user,
            format="cades",
            status="pending_otp",
        )
        with patch.object(
            type(sig.document_version.file),
            "path",
            new_callable=PropertyMock,
            side_effect=ValueError("no local path"),
        ):
            r = signer_client.post(f"/api/signatures/{sig.id}/resend_otp/", {}, format="json")
        assert r.status_code == status.HTTP_200_OK
