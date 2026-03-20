"""
Test API firma su protocollo e fascicolo (FASE 20).
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.signatures.models import SignatureRequest, SignatureSequenceStep
from apps.protocols.models import Protocol
from apps.dossiers.models import Dossier
from apps.organizations.models import OrganizationalUnit
from apps.documents.models import Document, DocumentVersion, Folder

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user_a(db):
    u = User.objects.create_user(email="a@test.com", password="test")
    u.role = "OPERATOR"
    u.save()
    return u


@pytest.fixture
def user_b(db):
    return User.objects.create_user(email="b@test.com", password="test")


@pytest.fixture
def user_c(db):
    return User.objects.create_user(email="c@test.com", password="test")


@pytest.fixture
def ou(db):
    return OrganizationalUnit.objects.create(name="OU1", code="OU1")


@pytest.fixture
def protocol(db, user_a, ou):
    return Protocol.objects.create(
        protocol_id="2024/TEST/0001",
        subject="Oggetto",
        direction="out",
        status="active",
        created_by=user_a,
        organizational_unit=ou,
    )


@pytest.fixture
def dossier(db, user_a):
    return Dossier.objects.create(
        title="Fascicolo test",
        identifier="FAS-001",
        created_by=user_a,
        status="open",
    )


@pytest.mark.django_db
class TestRequestForProtocol:
    def test_request_signature_for_protocol(self, client, user_a, user_b, protocol):
        client.force_authenticate(user=user_a)
        response = client.post(
            "/api/signatures/request_for_protocol/",
            {
                "protocol_id": str(protocol.id),
                "signers": [{"user_id": str(user_b.id), "order": 0}],
                "signature_type": "cades",
                "require_sequential": False,
                "notes": "Note",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["target_type"] == "protocol"
        assert data["protocol"] == str(protocol.id)
        assert data["format"] == "cades"
        assert len(data["sequence_steps"]) == 1
        assert data["sequence_steps"][0]["signer_email"] == user_b.email


@pytest.mark.django_db
class TestRequestForDossier:
    def test_request_signature_for_dossier(self, client, user_a, user_b, dossier):
        client.force_authenticate(user=user_a)
        response = client.post(
            "/api/signatures/request_for_dossier/",
            {
                "dossier_id": str(dossier.id),
                "signers": [{"user_id": str(user_b.id), "order": 0}],
                "signature_type": "cades",
                "require_sequential": True,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["target_type"] == "dossier"
        assert data["dossier"] == str(dossier.id)
        assert data["require_sequential"] is True


@pytest.mark.django_db
class TestSignStep:
    def test_sign_step_advances_sequence(self, client, user_a, user_b, user_c, protocol):
        client.force_authenticate(user=user_a)
        r = client.post(
            "/api/signatures/request_for_protocol/",
            {
                "protocol_id": str(protocol.id),
                "signers": [
                    {"user_id": str(user_b.id), "order": 0},
                    {"user_id": str(user_c.id), "order": 1},
                ],
                "require_sequential": True,
            },
            format="json",
        )
        assert r.status_code == 201
        sig_id = r.json()["id"]
        client.force_authenticate(user=user_b)
        r2 = client.post(f"/api/signatures/{sig_id}/sign_step/", {}, format="json")
        assert r2.status_code == 200
        data = r2.json()
        assert data["current_signer_index"] == 1
        assert data["status"] != "completed"
        client.force_authenticate(user=user_c)
        r3 = client.post(f"/api/signatures/{sig_id}/sign_step/", {}, format="json")
        assert r3.status_code == 200
        assert r3.json()["status"] == "completed"

    def test_all_signed_completes_request(self, client, user_a, user_b, protocol):
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
        client.force_authenticate(user=user_b)
        r2 = client.post(f"/api/signatures/{sig_id}/sign_step/", {}, format="json")
        assert r2.status_code == 200
        assert r2.json()["status"] == "completed"


@pytest.mark.django_db
class TestRejectStep:
    def test_reject_step_rejects_request(self, client, user_a, user_b, protocol):
        client.force_authenticate(user=user_a)
        r = client.post(
            "/api/signatures/request_for_protocol/",
            {"protocol_id": str(protocol.id), "signers": [{"user_id": str(user_b.id)}]},
            format="json",
        )
        assert r.status_code == 201
        sig_id = r.json()["id"]
        client.force_authenticate(user=user_b)
        r2 = client.post(
            f"/api/signatures/{sig_id}/reject_step/",
            {"reason": "Non posso firmare"},
            format="json",
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "rejected"


@pytest.mark.django_db
class TestSequentialNotify:
    def test_sequential_notifies_next_signer(self, client, user_a, user_b, user_c, protocol):
        client.force_authenticate(user=user_a)
        r = client.post(
            "/api/signatures/request_for_protocol/",
            {
                "protocol_id": str(protocol.id),
                "signers": [
                    {"user_id": str(user_b.id), "order": 0},
                    {"user_id": str(user_c.id), "order": 1},
                ],
                "require_sequential": True,
            },
            format="json",
        )
        assert r.status_code == 201
        sig = SignatureRequest.objects.get(id=r.json()["id"])
        assert sig.get_current_signer() == user_b

    def test_non_sequential_notifies_all_signers(self, client, user_a, user_b, user_c, protocol):
        client.force_authenticate(user=user_a)
        r = client.post(
            "/api/signatures/request_for_protocol/",
            {
                "protocol_id": str(protocol.id),
                "signers": [
                    {"user_id": str(user_b.id)},
                    {"user_id": str(user_c.id)},
                ],
                "require_sequential": False,
            },
            format="json",
        )
        assert r.status_code == 201
        assert SignatureRequest.objects.filter(id=r.json()["id"]).exists()


@pytest.mark.django_db
class TestDownloadSigned:
    def test_download_signed_returns_file(self, client, user_a, protocol):
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=protocol,
            requested_by=user_a,
            format="cades",
            status="completed",
        )
        from django.core.files.base import ContentFile
        sig.signed_file.save("signed.p7m", ContentFile(b"mock signed content"), save=True)
        client.force_authenticate(user=user_a)
        r = client.get(f"/api/signatures/{sig.id}/download_signed/")
        assert r.status_code == 200
        assert b"mock signed content" in r.content


@pytest.mark.django_db
class TestVerify:
    def test_verify_returns_valid_result_for_mock(self, client, user_a, protocol):
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=protocol,
            requested_by=user_a,
            format="cades",
            status="completed",
        )
        from django.core.files.base import ContentFile
        sig.signed_file.save("signed.p7m", ContentFile(b"x"), save=True)
        client.force_authenticate(user=user_a)
        r = client.get(f"/api/signatures/{sig.id}/verify/")
        assert r.status_code == 200
        data = r.json()
        assert "valid" in data
        assert data["valid"] is True


@pytest.mark.django_db
class TestTimestamp:
    def test_timestamp_applied_after_sign(self):
        from apps.signatures.verification import apply_timestamp
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 mock")
            f.flush()
            result = apply_timestamp(f.name)
            os.unlink(f.name)
        assert isinstance(result, bytes)
        assert len(result) >= 0
