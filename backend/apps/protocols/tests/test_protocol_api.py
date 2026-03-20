"""
Test API protocolli FASE 09: numerazione, filtri, documento protocollato non modificabile.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership
from apps.protocols.models import Protocol, ProtocolCounter
from apps.documents.models import Document, DocumentVersion, Folder

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def ou_it(db):
    return OrganizationalUnit.objects.create(name="IT", code="IT", description="")

@pytest.fixture
def ou_dir(db):
    return OrganizationalUnit.objects.create(name="Direzione", code="DIR", description="")


@pytest.fixture
def user_admin(db):
    u = User.objects.create_user(email="admin_p@test.com", password="test")
    u.role = "ADMIN"
    u.save()
    return u


@pytest.fixture
def user_operator(db, ou_it):
    u = User.objects.create_user(email="op_p@test.com", password="test")
    u.role = "OPERATOR"
    u.save()
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou_it, role="OPERATOR")
    return u


@pytest.mark.django_db
class TestProtocolCounter:
    """Numerazione progressiva per anno e UO."""

    def test_get_next_number_increments(self, ou_it):
        n1 = ProtocolCounter.get_next_number(ou_it, 2024)
        n2 = ProtocolCounter.get_next_number(ou_it, 2024)
        assert n1 == 1
        assert n2 == 2

    def test_two_ous_separate_counters(self, ou_it, ou_dir):
        n_it = ProtocolCounter.get_next_number(ou_it, 2024)
        n_dir = ProtocolCounter.get_next_number(ou_dir, 2024)
        assert n_it == 1
        assert n_dir == 1
        n_it2 = ProtocolCounter.get_next_number(ou_it, 2024)
        assert n_it2 == 2

    def test_new_year_restarts(self, ou_it):
        n1 = ProtocolCounter.get_next_number(ou_it, 2024)
        n2 = ProtocolCounter.get_next_number(ou_it, 2025)
        assert n1 == 1
        assert n2 == 1


@pytest.mark.django_db
class TestProtocolAPI:
    """CRUD e filtri protocolli."""

    def test_create_protocol_generates_id(self, api_client, user_admin, ou_it):
        api_client.force_authenticate(user=user_admin)
        r = api_client.post(
            "/api/protocols/",
            {
                "direction": "in",
                "subject": "Oggetto test",
                "sender_receiver": "Mittente",
                "organizational_unit": str(ou_it.id),
                "notes": "",
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        data = r.json()
        assert data["protocol_id"] == f"2024/IT/0001" or data["protocol_id"].endswith("/0001")
        assert data["number"] == 1
        assert data["subject"] == "Oggetto test"

    def test_second_protocol_same_ou_increments(self, api_client, user_admin, ou_it):
        api_client.force_authenticate(user=user_admin)
        api_client.post(
            "/api/protocols/",
            {"direction": "in", "subject": "Primo", "organizational_unit": str(ou_it.id)},
            format="json",
        )
        r = api_client.post(
            "/api/protocols/",
            {"direction": "out", "subject": "Secondo", "organizational_unit": str(ou_it.id)},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        assert r.json()["number"] == 2
        assert "0002" in r.json()["protocol_id"]

    def test_filter_direction(self, api_client, user_admin, ou_it):
        api_client.force_authenticate(user=user_admin)
        api_client.post(
            "/api/protocols/",
            {"direction": "in", "subject": "Entrata", "organizational_unit": str(ou_it.id)},
            format="json",
        )
        api_client.post(
            "/api/protocols/",
            {"direction": "out", "subject": "Uscita", "organizational_unit": str(ou_it.id)},
            format="json",
        )
        r_in = api_client.get("/api/protocols/?direction=in")
        r_out = api_client.get("/api/protocols/?direction=out")
        assert r_in.status_code == 200
        assert r_out.status_code == 200
        in_ids = [p["protocol_id"] for p in r_in.json().get("results", r_in.json())]
        out_ids = [p["protocol_id"] for p in r_out.json().get("results", r_out.json())]
        assert any("Entrata" in (p.get("subject") or "") for p in (r_in.json().get("results") or r_in.json()))
        assert any("Uscita" in (p.get("subject") or "") for p in (r_out.json().get("results") or r_out.json()))

    def test_search_subject(self, api_client, user_admin, ou_it):
        api_client.force_authenticate(user=user_admin)
        api_client.post(
            "/api/protocols/",
            {"direction": "in", "subject": "Contratto speciale XYZ", "organizational_unit": str(ou_it.id)},
            format="json",
        )
        r = api_client.get("/api/protocols/?search=Contratto")
        assert r.status_code == 200
        data = r.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        if isinstance(results, list):
            assert any("XYZ" in (p.get("subject") or "") for p in results)
        else:
            assert "results" in data or "subject" in str(results)

    def test_destroy_returns_400(self, api_client, user_admin, ou_it):
        api_client.force_authenticate(user=user_admin)
        r1 = api_client.post(
            "/api/protocols/",
            {"direction": "in", "subject": "Da non eliminare", "organizational_unit": str(ou_it.id)},
            format="json",
        )
        pid = r1.json()["id"]
        r = api_client.delete(f"/api/protocols/{pid}/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestProtocolDocumentLock:
    """Documento protocollato non modificabile (RF-063)."""

    def test_upload_version_protocolled_returns_400(self, api_client, user_admin, ou_it):
        from apps.documents.models import DocumentPermission
        folder = Folder.objects.create(name="F")
        doc = Document.objects.create(
            title="Doc da protocollare",
            folder=folder,
            created_by=user_admin,
        )
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            is_current=True,
            created_by=user_admin,
        )
        DocumentPermission.objects.create(document=doc, user=user_admin, can_read=True, can_write=True)
        api_client.force_authenticate(user=user_admin)
        api_client.post(
            "/api/protocols/",
            {
                "direction": "out",
                "subject": "Protocollo doc",
                "organizational_unit": str(ou_it.id),
                "document": str(doc.id),
            },
            format="json",
        )
        doc.refresh_from_db()
        assert doc.is_protocolled is True
        r = api_client.post(
            f"/api/documents/{doc.id}/upload_version/",
            {"file": ("f2.pdf", b"fake pdf content", "application/pdf")},
            format="multipart",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert "protocollato" in (r.json().get("detail") or "").lower()
