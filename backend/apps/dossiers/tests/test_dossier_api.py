"""
Test API fascicoli FASE 09 (RF-064..RF-069).
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership
from apps.dossiers.models import Dossier, DossierDocument, DossierProtocol, DossierPermission
from apps.documents.models import Document, Folder
from apps.protocols.models import Protocol

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def ou(db):
    return OrganizationalUnit.objects.create(name="IT", code="IT")


@pytest.fixture
def user_admin(db):
    u = User.objects.create_user(email="admin_d@test.com", password="test")
    u.role = "ADMIN"
    u.save()
    return u


@pytest.fixture
def user_approver(db):
    u = User.objects.create_user(email="approver_d@test.com", password="test")
    u.role = "APPROVER"
    u.save()
    return u


@pytest.fixture
def user_operator(db, ou):
    u = User.objects.create_user(email="op_d@test.com", password="test")
    u.role = "OPERATOR"
    u.save()
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.mark.django_db
class TestDossierCRUD:
    def test_create_dossier_admin(self, api_client, user_admin):
        api_client.force_authenticate(user=user_admin)
        r = api_client.post(
            "/api/dossiers/",
            {"title": "Fascicolo test", "identifier": "FASC-001", "description": "Desc"},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        assert r.json()["identifier"] == "FASC-001"
        assert r.json()["status"] == "open"

    def test_create_dossier_approver(self, api_client, user_approver):
        api_client.force_authenticate(user=user_approver)
        r = api_client.post(
            "/api/dossiers/",
            {"title": "Fascicolo approv", "identifier": "FASC-002"},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED

    def test_create_dossier_operator_forbidden(self, api_client, user_operator):
        api_client.force_authenticate(user=user_operator)
        r = api_client.post(
            "/api/dossiers/",
            {"title": "F", "identifier": "FASC-003"},
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_identifier_unique_returns_400(self, api_client, user_admin):
        api_client.force_authenticate(user=user_admin)
        api_client.post(
            "/api/dossiers/",
            {"title": "Uno", "identifier": "UNICO-1"},
            format="json",
        )
        r = api_client.post(
            "/api/dossiers/",
            {"title": "Due", "identifier": "UNICO-1"},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert "identifier" in (r.json() or {})


@pytest.mark.django_db
class TestDossierFilters:
    def test_filter_mine(self, api_client, user_operator, ou):
        api_client.force_authenticate(user=user_operator)
        d = Dossier.objects.create(
            title="Mio", identifier="MIO-1", created_by=user_operator, responsible=user_operator
        )
        DossierPermission.objects.create(dossier=d, user=user_operator, can_read=True)
        r = api_client.get("/api/dossiers/?filter=mine")
        assert r.status_code == 200
        data = r.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        if isinstance(results, list):
            assert len(results) >= 1
            assert any(x.get("identifier") == "MIO-1" for x in results)

    def test_filter_archived(self, api_client, user_admin):
        api_client.force_authenticate(user=user_admin)
        Dossier.objects.create(
            title="Arch", identifier="ARCH-1", status="archived", created_by=user_admin
        )
        r = api_client.get("/api/dossiers/?filter=all&status=archived")
        assert r.status_code == 200


@pytest.mark.django_db
class TestDossierArchive:
    def test_archive_with_non_approved_document_returns_400(self, api_client, user_admin):
        api_client.force_authenticate(user=user_admin)
        folder = Folder.objects.create(name="F")
        doc = Document.objects.create(
            title="Doc", folder=folder, created_by=user_admin, status="DRAFT"
        )
        dossier = Dossier.objects.create(
            title="D", identifier="D-1", created_by=user_admin, responsible=user_admin
        )
        DossierDocument.objects.create(dossier=dossier, document=doc, added_by=user_admin)
        r = api_client.post(f"/api/dossiers/{dossier.id}/archive/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert "non approvati" in (r.json().get("detail") or "")

    def test_archive_with_all_approved_ok(self, api_client, user_admin):
        api_client.force_authenticate(user=user_admin)
        folder = Folder.objects.create(name="F")
        doc = Document.objects.create(
            title="Doc", folder=folder, created_by=user_admin, status="APPROVED"
        )
        dossier = Dossier.objects.create(
            title="D", identifier="D-2", created_by=user_admin, responsible=user_admin
        )
        DossierDocument.objects.create(dossier=dossier, document=doc, added_by=user_admin)
        r = api_client.post(f"/api/dossiers/{dossier.id}/archive/")
        assert r.status_code == 200
        dossier.refresh_from_db()
        assert dossier.status == "archived"


@pytest.mark.django_db
class TestDossierDocuments:
    def test_add_remove_document(self, api_client, user_admin):
        api_client.force_authenticate(user=user_admin)
        folder = Folder.objects.create(name="F")
        doc = Document.objects.create(title="Doc", folder=folder, created_by=user_admin)
        dossier = Dossier.objects.create(
            title="D", identifier="DD-1", created_by=user_admin, responsible=user_admin
        )
        r = api_client.post(
            f"/api/dossiers/{dossier.id}/add_document/",
            {"document_id": str(doc.id), "notes": "Nota"},
            format="json",
        )
        assert r.status_code == 200
        assert DossierDocument.objects.filter(dossier=dossier, document=doc).exists()
        r2 = api_client.delete(f"/api/dossiers/{dossier.id}/remove_document/{doc.id}/")
        assert r2.status_code == 200
        assert not DossierDocument.objects.filter(dossier=dossier, document=doc).exists()


@pytest.mark.django_db
class TestDossierProtocols:
    def test_add_protocol(self, api_client, user_admin, ou):
        api_client.force_authenticate(user=user_admin)
        protocol = Protocol.objects.create(
            number=1, year=2024, organizational_unit=ou,
            protocol_id="2024/IT/0001", direction="in", subject="P",
            registered_by=user_admin, created_by=user_admin,
        )
        dossier = Dossier.objects.create(
            title="D", identifier="DP-1", created_by=user_admin, responsible=user_admin
        )
        r = api_client.post(
            f"/api/dossiers/{dossier.id}/add_protocol/",
            {"protocol_id": str(protocol.id)},
            format="json",
        )
        assert r.status_code == 200
        assert DossierProtocol.objects.filter(dossier=dossier, protocol=protocol).exists()


@pytest.mark.django_db
class TestDossierPermission:
    def test_user_without_permission_403(self, api_client, user_operator, user_admin):
        api_client.force_authenticate(user=user_operator)
        dossier = Dossier.objects.create(
            title="Privato", identifier="PRIV-1", created_by=user_admin, responsible=user_admin
        )
        r = api_client.get(f"/api/dossiers/{dossier.id}/")
        assert r.status_code == status.HTTP_403_FORBIDDEN
