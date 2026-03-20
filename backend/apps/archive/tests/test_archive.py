"""
Test API archivio e pacchetti AGID (FASE 21).
"""
import io
import zipfile
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.archive.models import DocumentArchive, RetentionRule, InformationPackage
from apps.archive.packager import AgidPackager
from apps.archive.classification import TITOLARIO_DEFAULT
from apps.documents.models import Document, DocumentVersion, Folder
from apps.protocols.models import Protocol
from apps.dossiers.models import Dossier
from apps.organizations.models import OrganizationalUnit

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user_admin(db):
    u = User.objects.create_user(email="admin@test.com", password="test")
    u.role = "ADMIN"
    u.save()
    return u


@pytest.fixture
def user_approver(db):
    u = User.objects.create_user(email="approver@test.com", password="test")
    u.role = "APPROVER"
    u.save()
    return u


@pytest.fixture
def folder(db, user_admin):
    return Folder.objects.create(name="F", created_by=user_admin)


@pytest.fixture
def doc(db, folder, user_admin):
    d = Document.objects.create(
        title="Doc test",
        folder=folder,
        created_by=user_admin,
        status=Document.STATUS_APPROVED,
    )
    DocumentVersion.objects.create(
        document=d,
        version_number=1,
        file_name="f.pdf",
        is_current=True,
        created_by=user_admin,
    )
    return d


@pytest.fixture
def ou(db):
    return OrganizationalUnit.objects.create(name="OU1", code="OU1")


@pytest.fixture
def protocol(db, user_admin, ou):
    return Protocol.objects.create(
        protocol_id="2024/TEST/0001",
        subject="Oggetto",
        direction="out",
        status="active",
        created_by=user_admin,
        organizational_unit=ou,
    )


@pytest.fixture
def dossier(db, user_admin):
    return Dossier.objects.create(
        title="Fascicolo",
        identifier="FAS-1",
        created_by=user_admin,
        status="open",
    )


@pytest.mark.django_db
class TestDocumentArchiveCreated:
    def test_document_archive_created_on_document_save(self, doc):
        rec = DocumentArchive.objects.filter(document=doc).first()
        assert rec is not None
        assert rec.stage == "current"


@pytest.mark.django_db
class TestMoveToDeposit:
    def test_move_to_deposit(self, client, user_approver, doc):
        rec = DocumentArchive.objects.get(document=doc)
        client.force_authenticate(user=user_approver)
        r = client.post(f"/api/archive/documents/{rec.id}/move_to_deposit/", {"notes": "Ok"}, format="json")
        assert r.status_code == 200
        rec.refresh_from_db()
        assert rec.stage == "deposit"
        assert rec.archive_date is not None


@pytest.mark.django_db
class TestMoveToHistorical:
    def test_move_to_historical(self, client, user_admin, doc):
        rec = DocumentArchive.objects.get(document=doc)
        rec.stage = "deposit"
        rec.archive_date = rec.updated_at
        rec.save()
        client.force_authenticate(user=user_admin)
        r = client.post(f"/api/archive/documents/{rec.id}/move_to_historical/", {}, format="json")
        assert r.status_code == 200
        rec.refresh_from_db()
        assert rec.stage == "historical"


@pytest.mark.django_db
class TestCreatePdv:
    def test_create_pdv_generates_zip(self, client, user_admin, doc, protocol, dossier):
        client.force_authenticate(user=user_admin)
        r = client.post(
            "/api/archive/packages/create_pdv/",
            {
                "document_ids": [str(doc.id)],
                "protocol_ids": [str(protocol.id)],
                "dossier_ids": [str(dossier.id)],
            },
            format="json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["package_type"] == "PdV"
        assert data["status"] == "ready"
        pkg = InformationPackage.objects.get(id=data["id"])
        assert pkg.package_file

    def test_pdv_contains_manifest(self, client, user_admin, doc):
        client.force_authenticate(user=user_admin)
        r = client.post(
            "/api/archive/packages/create_pdv/",
            {"document_ids": [str(doc.id)]},
            format="json",
        )
        assert r.status_code == 201
        pkg = InformationPackage.objects.get(id=r.json()["id"])
        assert pkg.manifest_file
        pkg.manifest_file.open("r")
        content = pkg.manifest_file.read()
        pkg.manifest_file.close()
        import json
        manifest = json.loads(content)
        assert manifest["type"] == "PdV"
        assert str(doc.id) in manifest["document_ids"]

    def test_pdv_contains_document_metadata(self, client, user_admin, doc):
        packager = AgidPackager()
        zip_bytes, manifest = packager.generate_pdv([doc])
        z = zipfile.ZipFile(io.BytesIO(zip_bytes), "r")
        names = z.namelist()
        assert "manifest.json" in names
        assert any("metadata.json" in n for n in names)
        assert "checksums.sha256" in names
        z.close()


@pytest.mark.django_db
class TestSendToConservator:
    def test_send_to_conservator_mock(self, client, user_admin, doc):
        client.force_authenticate(user=user_admin)
        r = client.post(
            "/api/archive/packages/create_pdv/",
            {"document_ids": [str(doc.id)]},
            format="json",
        )
        assert r.status_code == 201
        pkg_id = r.json()["id"]
        r2 = client.post(f"/api/archive/packages/{pkg_id}/send_to_conservator/", {}, format="json")
        assert r2.status_code == 200
        assert r2.json()["status"] == "accepted"


@pytest.mark.django_db
class TestRetentionRuleCrud:
    def test_retention_rule_crud(self, client, user_admin):
        client.force_authenticate(user=user_admin)
        r = client.post(
            "/api/archive/retention-rules/",
            {
                "classification_code": "0.0",
                "classification_label": "Test",
                "retention_years": 5,
                "action_after_retention": "discard",
            },
            format="json",
        )
        assert r.status_code == 201
        rule_id = r.json()["id"]
        r2 = client.get(f"/api/archive/retention-rules/{rule_id}/")
        assert r2.status_code == 200
        r3 = client.delete(f"/api/archive/retention-rules/{rule_id}/")
        assert r3.status_code == 204


@pytest.mark.django_db
class TestInitTitolarioCommand:
    def test_init_titolario_command_creates_rules(self):
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command("init_titolario", stdout=out)
        count = RetentionRule.objects.count()
        assert count > 0
        codes = set(RetentionRule.objects.values_list("classification_code", flat=True))
        assert "1.1" in codes or "1.2" in codes


@pytest.mark.django_db
class TestTitolarioApi:
    def test_titolario_api_returns_tree(self, client, user_admin):
        from django.core.management import call_command
        call_command("init_titolario")
        client.force_authenticate(user=user_admin)
        r = client.get("/api/archive/titolario/")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "code" in data[0] and "label" in data[0]

    def test_titolario_detail_by_code(self, client, user_admin):
        from django.core.management import call_command
        call_command("init_titolario")
        client.force_authenticate(user=user_admin)
        r = client.get("/api/archive/titolario/1.1/")
        assert r.status_code == 200
        assert r.json()["classification_code"] == "1.1"
