"""Test estesi DossierViewSet (FASE 33C)."""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentVersion, Folder
from apps.dossiers.models import Dossier, DossierDocument
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.protocols.models import Protocol

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Organizzazione Default", "plan": "enterprise"},
    )
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="DSX OU", code="DSX", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(email="dsx-adm@test.com", password="Test123!", role="ADMIN")
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def operator_user(db, tenant, ou):
    u = User.objects.create_user(email="dsx-op@test.com", password="Test123!", role="OPERATOR")
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
def operator_client(operator_user):
    c = APIClient()
    c.force_authenticate(user=operator_user)
    return c


@pytest.fixture
def dossier(db, tenant, admin_user, ou):
    return Dossier.objects.create(
        title="Dossier Ext",
        identifier="DSX-EXT-001",
        tenant=tenant,
        responsible=admin_user,
        created_by=admin_user,
        organizational_unit=ou,
        status="open",
    )


@pytest.fixture
def approved_document(db, tenant, admin_user):
    folder = Folder.objects.create(name="DF", tenant=tenant, created_by=admin_user)
    doc = Document.objects.create(
        title="Approved for dossier",
        tenant=tenant,
        folder=folder,
        created_by=admin_user,
        owner=admin_user,
        status=Document.STATUS_APPROVED,
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        file_name="f.pdf",
        created_by=admin_user,
        is_current=True,
    )
    doc.current_version = 1
    doc.save(update_fields=["current_version"])
    return doc


@pytest.fixture
def protocol_for_dossier(db, tenant, admin_user, ou):
    return Protocol.objects.create(
        protocol_id="2099/DSX/0001",
        subject="P",
        direction="in",
        status="active",
        created_by=admin_user,
        organizational_unit=ou,
        tenant=tenant,
    )


@pytest.mark.django_db
class TestDossierExportsAndList:
    def test_export_excel(self, admin_client):
        r = admin_client.get("/api/dossiers/export_excel/")
        assert r.status_code == 200
        assert "spreadsheet" in r["Content-Type"]

    def test_export_pdf(self, admin_client):
        r = admin_client.get("/api/dossiers/export_pdf/")
        assert r.status_code == 200

    def test_list_filters_responsible_ou(self, admin_client, dossier, admin_user, ou):
        r = admin_client.get(
            "/api/dossiers/",
            {"filter": "all", "responsible_id": str(admin_user.id), "ou_id": str(ou.id)},
        )
        assert r.status_code == 200


@pytest.mark.django_db
class TestDossierAssociations:
    def test_add_remove_document(self, admin_client, dossier, approved_document):
        r = admin_client.post(
            f"/api/dossiers/{dossier.id}/add_document/",
            {"document_id": str(approved_document.id)},
            format="json",
        )
        assert r.status_code == 200
        r2 = admin_client.delete(f"/api/dossiers/{dossier.id}/remove_document/{approved_document.id}/")
        assert r2.status_code == 200

    def test_add_remove_protocol(self, admin_client, dossier, protocol_for_dossier):
        r = admin_client.post(
            f"/api/dossiers/{dossier.id}/add_protocol/",
            {"protocol_id": str(protocol_for_dossier.id)},
            format="json",
        )
        assert r.status_code == 200
        r2 = admin_client.delete(
            f"/api/dossiers/{dossier.id}/remove_protocol/{protocol_for_dossier.id}/"
        )
        assert r2.status_code == 200

    def test_documents_protocols_detail_full_chat(self, admin_client, dossier, approved_document):
        admin_client.post(
            f"/api/dossiers/{dossier.id}/add_document/",
            {"document_id": str(approved_document.id)},
            format="json",
        )
        r = admin_client.get(f"/api/dossiers/{dossier.id}/documents/")
        assert r.status_code == 200
        r2 = admin_client.get(f"/api/dossiers/{dossier.id}/protocols/")
        assert r2.status_code == 200
        r3 = admin_client.get(f"/api/dossiers/{dossier.id}/detail_full/")
        assert r3.status_code == 200
        r4 = admin_client.post(f"/api/dossiers/{dossier.id}/chat/", {}, format="json")
        assert r4.status_code == 200


@pytest.mark.django_db
class TestDossierFoldersEmailFile:
    def test_add_remove_folder(self, admin_client, dossier, admin_user, tenant):
        folder = Folder.objects.create(name="In Dossier", tenant=tenant, created_by=admin_user)
        r = admin_client.post(
            f"/api/dossiers/{dossier.id}/add_folder/",
            {"folder_id": str(folder.id)},
            format="json",
        )
        assert r.status_code == 200
        from apps.dossiers.models import DossierFolder

        df = DossierFolder.objects.filter(dossier=dossier, folder=folder).first()
        assert df
        r2 = admin_client.post(
            f"/api/dossiers/{dossier.id}/remove_folder/",
            {"dossier_folder_id": str(df.id)},
            format="json",
        )
        assert r2.status_code == 200

    def test_add_email(self, admin_client, dossier):
        r = admin_client.post(
            f"/api/dossiers/{dossier.id}/add_email/",
            {
                "email_type": "pec",
                "from_address": "a@pec.it",
                "to_addresses": ["b@pec.it"],
                "subject": "S",
                "body": "Body",
            },
            format="json",
        )
        assert r.status_code == 201

    def test_upload_file(self, admin_client, dossier):
        f = SimpleUploadedFile("up.bin", b"data", content_type="application/octet-stream")
        r = admin_client.post(
            f"/api/dossiers/{dossier.id}/upload_file/",
            {"file": f, "notes": "n"},
            format="multipart",
        )
        assert r.status_code == 201


@pytest.mark.django_db
class TestDossierCloseIndexAgid:
    def test_close_dossier(self, admin_client, dossier):
        r = admin_client.post(f"/api/dossiers/{dossier.id}/close/", {}, format="json")
        assert r.status_code == 200
        dossier.refresh_from_db()
        assert dossier.status == "closed"

    @patch("apps.dossiers.index_generator.generate_dossier_index_pdf", return_value=b"%PDF-1.4 idx")
    def test_generate_index(self, mock_pdf, admin_client, dossier):
        r = admin_client.get(f"/api/dossiers/{dossier.id}/generate_index/")
        assert r.status_code == 200
        assert r["Content-Type"] == "application/pdf"

    @patch("apps.metadata.agid_metadata.get_agid_metadata_for_dossier", return_value={"k": "v"})
    def test_agid_metadata(self, mock_meta, admin_client, dossier):
        r = admin_client.get(f"/api/dossiers/{dossier.id}/agid_metadata/")
        assert r.status_code == 200
        assert r.json() == {"k": "v"}


@pytest.mark.django_db
class TestDossierArchiveAndPermissions:
    def test_archive_when_all_docs_approved(self, admin_client, dossier, approved_document):
        DossierDocument.objects.get_or_create(
            dossier=dossier,
            document=approved_document,
            defaults={"added_by": dossier.created_by},
        )
        r = admin_client.post(f"/api/dossiers/{dossier.id}/archive/", {}, format="json")
        assert r.status_code == 200
        dossier.refresh_from_db()
        assert dossier.status == "archived"

    def test_operator_cannot_create_dossier(self, operator_client):
        r = operator_client.post(
            "/api/dossiers/",
            {"title": "X", "identifier": "DSX-OP-001"},
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN
