"""Copertura lista richieste firma: filtri e permessi ADMIN (FASE 33)."""
import pytest
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from apps.documents.models import Document, Folder
from apps.signatures.models import SignatureRequest

User = get_user_model()


@pytest.fixture
def folder(db):
    return Folder.objects.create(name="SigFolder")


@pytest.mark.django_db
class TestSignaturesListCoverage:
    def test_admin_lists_all_signature_requests(self, folder):
        admin = User.objects.create_user(email="sig-adm@test.com", password="x", role="ADMIN")
        alice = User.objects.create_user(email="sig-alice@test.com", password="x", role="OPERATOR")
        bob = User.objects.create_user(email="sig-bob@test.com", password="x", role="OPERATOR")
        doc = Document.objects.create(
            title="D",
            folder=folder,
            created_by=alice,
            status=Document.STATUS_APPROVED,
        )
        sr = SignatureRequest.objects.create(
            document=doc,
            requested_by=alice,
            signer=bob,
            format="pades_invisible",
            status="pending_otp",
        )
        c = APIClient()
        c.force_authenticate(user=admin)
        r = c.get("/api/signatures/")
        assert r.status_code == 200
        results = r.data.get("results", r.data) if isinstance(r.data, dict) else r.data
        ids = {str(x["id"]) for x in results}
        assert str(sr.id) in ids

    def test_filter_by_target_document(self, folder):
        admin = User.objects.create_user(email="sig-adm2@test.com", password="x", role="ADMIN")
        u = User.objects.create_user(email="sig-u@test.com", password="x", role="OPERATOR")
        doc = Document.objects.create(
            title="Dx",
            folder=folder,
            created_by=u,
            status=Document.STATUS_APPROVED,
        )
        SignatureRequest.objects.create(
            document=doc,
            requested_by=u,
            signer=u,
            format="cades",
            status="completed",
        )
        c = APIClient()
        c.force_authenticate(user=admin)
        r = c.get("/api/signatures/", {"target_type": "document", "target_id": str(doc.id)})
        assert r.status_code == 200
        if isinstance(r.data, dict):
            assert r.data["count"] >= 1
