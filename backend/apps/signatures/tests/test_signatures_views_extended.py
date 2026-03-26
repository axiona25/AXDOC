"""Copertura aggiuntiva SignatureRequestViewSet (FASE 33B)."""
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.organizations.models import OrganizationalUnit
from apps.protocols.models import Protocol
from apps.signatures.models import SignatureRequest

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user_a(db):
    u = User.objects.create_user(email="ext-a@test.com", password="test")
    u.role = "OPERATOR"
    u.save()
    return u


@pytest.fixture
def user_b(db):
    u = User.objects.create_user(email="ext-b@test.com", password="test")
    u.role = "OPERATOR"
    u.save()
    return u


@pytest.fixture
def outsider(db):
    return User.objects.create_user(email="ext-out@test.com", password="test", role="OPERATOR")


@pytest.fixture
def ou(db):
    return OrganizationalUnit.objects.create(name="OU-EXT", code="OUEXT")


@pytest.fixture
def protocol(db, user_a, ou):
    return Protocol.objects.create(
        protocol_id="2025/EXT/0001",
        subject="S",
        direction="out",
        status="active",
        created_by=user_a,
        organizational_unit=ou,
    )


@pytest.mark.django_db
class TestRequestForProtocolExtended:
    def test_protocol_not_found(self, client, user_a):
        client.force_authenticate(user=user_a)
        r = client.post(
            "/api/signatures/request_for_protocol/",
            {"protocol_id": str(uuid.uuid4()), "signers": [{"user_id": str(user_a.id)}]},
            format="json",
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_missing_signers(self, client, user_a, protocol):
        client.force_authenticate(user=user_a)
        r = client.post(
            "/api/signatures/request_for_protocol/",
            {"protocol_id": str(protocol.id), "signers": []},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestRequestForDossierExtended:
    def test_dossier_not_found(self, client, user_a):
        client.force_authenticate(user=user_a)
        r = client.post(
            "/api/signatures/request_for_dossier/",
            {"dossier_id": str(uuid.uuid4()), "signers": [{"user_id": str(user_a.id)}]},
            format="json",
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestSignStepRejectPermissions:
    def test_sign_step_forbidden_wrong_user(self, client, user_a, user_b, outsider, protocol):
        client.force_authenticate(user=user_a)
        r = client.post(
            "/api/signatures/request_for_protocol/",
            {
                "protocol_id": str(protocol.id),
                "signers": [{"user_id": str(user_b.id)}],
                "require_sequential": False,
            },
            format="json",
        )
        assert r.status_code == 201
        sig_id = r.json()["id"]
        client.force_authenticate(user=outsider)
        r2 = client.post(f"/api/signatures/{sig_id}/sign_step/", {}, format="json")
        assert r2.status_code == status.HTTP_404_NOT_FOUND

    def test_reject_step_forbidden_wrong_user(self, client, user_a, user_b, outsider, protocol):
        client.force_authenticate(user=user_a)
        r = client.post(
            "/api/signatures/request_for_protocol/",
            {"protocol_id": str(protocol.id), "signers": [{"user_id": str(user_b.id)}]},
            format="json",
        )
        sig_id = r.json()["id"]
        client.force_authenticate(user=outsider)
        r2 = client.post(f"/api/signatures/{sig_id}/reject_step/", {"reason": "x"}, format="json")
        assert r2.status_code == status.HTTP_404_NOT_FOUND

    def test_status_detail_includes_steps(self, client, user_a, user_b, protocol):
        client.force_authenticate(user=user_a)
        r = client.post(
            "/api/signatures/request_for_protocol/",
            {"protocol_id": str(protocol.id), "signers": [{"user_id": str(user_b.id)}]},
            format="json",
        )
        sig_id = r.json()["id"]
        r2 = client.get(f"/api/signatures/{sig_id}/status_detail/")
        assert r2.status_code == 200
        body = r2.json()
        assert "sequence_steps" in body
        assert len(body["sequence_steps"]) == 1


@pytest.mark.django_db
class TestRetrieveNotInQueryset:
    def test_outsider_cannot_retrieve_signature(self, client, user_a, user_b, outsider, protocol):
        client.force_authenticate(user=user_a)
        r = client.post(
            "/api/signatures/request_for_protocol/",
            {"protocol_id": str(protocol.id), "signers": [{"user_id": str(user_b.id)}]},
            format="json",
        )
        sig_id = r.json()["id"]
        client.force_authenticate(user=outsider)
        r2 = client.get(f"/api/signatures/{sig_id}/")
        assert r2.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestVerifyDownloadEdgeCases:
    def test_verify_without_signed_file(self, client, user_a, protocol):
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=protocol,
            requested_by=user_a,
            format="cades",
            status="completed",
        )
        client.force_authenticate(user=user_a)
        r = client.get(f"/api/signatures/{sig.id}/verify/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert r.json().get("valid") is False

    def test_download_signed_missing_file(self, client, user_a, protocol):
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=protocol,
            requested_by=user_a,
            format="cades",
            status="completed",
        )
        client.force_authenticate(user=user_a)
        r = client.get(f"/api/signatures/{sig.id}/download_signed/")
        assert r.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@pytest.mark.django_db
class TestVerifyExtractP7mApi:
    def test_verify_p7m_upload(self, client, user_a):
        client.force_authenticate(user=user_a)
        f = SimpleUploadedFile("t.p7m", b"not-valid-der", content_type="application/pkcs7-mime")
        r = client.post("/api/verify_p7m/", {"file": f}, format="multipart")
        assert r.status_code == 200
        body = r.json()
        assert "valid" in body
        assert body.get("file_name") == "t.p7m"

    def test_verify_p7m_rejects_non_p7m(self, client, user_a):
        client.force_authenticate(user=user_a)
        f = SimpleUploadedFile("x.txt", b"a", content_type="text/plain")
        r = client.post("/api/verify_p7m/", {"file": f}, format="multipart")
        assert r.status_code == 400

    def test_verify_p7m_missing_file(self, client, user_a):
        client.force_authenticate(user=user_a)
        r = client.post("/api/verify_p7m/", {}, format="multipart")
        assert r.status_code == 400

    @patch("apps.signatures.verification.extract_p7m_content")
    def test_extract_p7m_download(self, mock_ex, client, user_a, tmp_path):
        out = tmp_path / "inner.pdf"
        out.write_bytes(b"%PDF-1.4 extracted")
        mock_ex.return_value = {
            "success": True,
            "extracted_path": str(out),
            "original_name": "inner.pdf",
            "content_type": "application/pdf",
        }
        client.force_authenticate(user=user_a)
        f = SimpleUploadedFile("pack.p7m", b"x", content_type="application/octet-stream")
        r = client.post("/api/extract_p7m/", {"file": f}, format="multipart")
        assert r.status_code == 200
        assert b"%PDF" in r.content

    @patch("apps.signatures.verification.extract_p7m_content")
    def test_extract_p7m_fails_returns_400(self, mock_ex, client, user_a):
        mock_ex.return_value = {"success": False, "error": "bad"}
        client.force_authenticate(user=user_a)
        f = SimpleUploadedFile("bad.p7m", b"x", content_type="application/octet-stream")
        r = client.post("/api/extract_p7m/", {"file": f}, format="multipart")
        assert r.status_code == 400


class TestResendOtpGuards:
    def test_resend_otp_wrong_status(self, client, user_a, user_b, protocol):
        client.force_authenticate(user=user_a)
        r = client.post(
            "/api/signatures/request_for_protocol/",
            {"protocol_id": str(protocol.id), "signers": [{"user_id": str(user_b.id)}]},
            format="json",
        )
        sig_id = r.json()["id"]
        sig = SignatureRequest.objects.get(id=sig_id)
        sig.status = "completed"
        sig.signer = user_b
        sig.save(update_fields=["status", "signer"])
        client.force_authenticate(user=user_b)
        r2 = client.post(f"/api/signatures/{sig_id}/resend_otp/", {}, format="json")
        assert r2.status_code == status.HTTP_400_BAD_REQUEST
